import time

from bitmovin_api_sdk import BitmovinApi
from bitmovin_api_sdk import S3Input, S3Output
from bitmovin_api_sdk import Encoding, CloudRegion
from bitmovin_api_sdk import EncodingOutput, AclEntry, AclPermission
from bitmovin_api_sdk import IngestInputStream, StreamSelectionMode, PresetConfiguration
from bitmovin_api_sdk import Stream, StreamInput, MuxingStream, StreamMode, ColorConfig
from bitmovin_api_sdk import AacAudioConfiguration, AacChannelLayout
from bitmovin_api_sdk import H264VideoConfiguration, CodecConfigType, ProfileH264, LevelH264, WeightedPredictionPFrames
from bitmovin_api_sdk import SpriteJpegConfig, SpriteCreationMode, ThumbnailAspectMode, Sprite, SpriteUnit
from bitmovin_api_sdk import Fmp4Muxing
from bitmovin_api_sdk import HlsManifest, HlsVersion, AudioMediaInfo, StreamInfo
from bitmovin_api_sdk import DashManifest, Period, VideoAdaptationSet, AudioAdaptationSet
from bitmovin_api_sdk import DashFmp4Representation, DashRepresentationType, DashRepresentationTypeMode
from bitmovin_api_sdk import MessageType, StartEncodingRequest
from bitmovin_api_sdk import Status

TEST_ITEM = "thumbnail-sprite-vtt-h264-aac-fmp4-hls-dash"

API_KEY = '<INSERT YOUR API KEY>'
ORG_ID = '<INSERT YOUR ORG ID>'

S3_INPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
S3_INPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
S3_INPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

INPUT_PATH = '/path/to/your/input/file.mp4'
# e.g. 'inputs/big_buck_bunny_1080p_h264.mov'

S3_OUTPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
S3_OUTPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
S3_OUTPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

# Thumbnail and Sprite settings
THUMBNAIL_WIDTH = 640  # width value of each thumbnail image
THUMBNAIL_HEIGHT = 360  # height value of each thumbnail image
THUMBNAIL_INTERVAL_IN_SECONDS = 10  # thumbnail generation interval in seconds
SPRITE_NAME = "sprite_%number%.jpg"  # sprite jpeg filename pattern
SPRITE_VTT_NAME = "sprite.vtt"  # sprite vtt filename
SPRITE_HTILES_NUM = 10  # the number of horizontal tiles in sprite jpeg
SPRITE_VTILES_NUM = 10  # the number of vertical tiles in sprite jpeg
SPRITE_JPEG_QUALITY = 75  # sprite jpeg image quality (0 - 100)

OUTPUT_BASE_PATH = f'output/{TEST_ITEM}/'

bitmovin_api = BitmovinApi(api_key=API_KEY, tenant_org_id=ORG_ID)

# Example H.264 encoding profiles, including different resolutions, bitrates, and profiles.
video_encoding_profiles = [
    dict(height=240,  bitrate=300000,  profile=ProfileH264.HIGH, level=None,       mode=StreamMode.STANDARD),
    dict(height=360,  bitrate=800000,  profile=ProfileH264.HIGH, level=None,       mode=StreamMode.STANDARD),
    dict(height=480,  bitrate=1200000, profile=ProfileH264.HIGH, level=None,       mode=StreamMode.STANDARD),
    dict(height=540,  bitrate=2000000, profile=ProfileH264.HIGH, level=None,       mode=StreamMode.STANDARD),
    dict(height=720,  bitrate=4000000, profile=ProfileH264.HIGH, level=None,       mode=StreamMode.STANDARD),
    dict(height=1080, bitrate=6000000, profile=ProfileH264.HIGH, level=LevelH264.L4, mode=StreamMode.STANDARD)
]

# Example AAC audio encoding profiles, each with a specified bitrate and sample rate.
audio_encoding_profiles = [
    dict(bitrate=128000, rate=48000),
    dict(bitrate=64000,  rate=44100)
]


def main():
    """
    Main entry point for the encoding script.
    This demonstrates a basic Bitmovin encoding workflow using H.264 video and AAC audio. Steps:
      1) Create S3 input/output
      2) Create an Encoding object
      3) Define video/audio input streams
      4) Create multiple H.264 streams, using advanced color/coding parameters
         - Additionally, create sprite and VTT thumbnail indexes from the highest
           resolution (e.g. 1080p) stream.
      5) Create multiple AAC streams
      6) Start the encoding (FMP4 muxing outputs)
      7) Generate HLS and DASH manifests
    """

    # 1) S3 Input/Output
    s3_input = bitmovin_api.encoding.inputs.s3.create(
        s3_input=S3Input(
            access_key=S3_INPUT_ACCESS_KEY,
            secret_key=S3_INPUT_SECRET_KEY,
            bucket_name=S3_INPUT_BUCKET_NAME,
            name='Test S3 Input'
        )
    )
    s3_output = bitmovin_api.encoding.outputs.s3.create(
        s3_output=S3Output(
            access_key=S3_OUTPUT_ACCESS_KEY,
            secret_key=S3_OUTPUT_SECRET_KEY,
            bucket_name=S3_OUTPUT_BUCKET_NAME,
            name='Test S3 Output'
        )
    )

    # 2) Encoding instance
    encoding = bitmovin_api.encoding.encodings.create(
        encoding=Encoding(
            name=f"[{TEST_ITEM}] {INPUT_PATH}",
            cloud_region=CloudRegion.AWS_AP_NORTHEAST_1,
            encoder_version='STABLE'
        )
    )

    # 3) Input Streams
    video_ingest_input_stream = bitmovin_api.encoding.encodings.input_streams.ingest.create(
        encoding_id=encoding.id,
        ingest_input_stream=IngestInputStream(
            input_id=s3_input.id,
            input_path=INPUT_PATH,
            selection_mode=StreamSelectionMode.VIDEO_RELATIVE,
            position=0
        )
    )
    audio_ingest_input_stream = bitmovin_api.encoding.encodings.input_streams.ingest.create(
        encoding_id=encoding.id,
        ingest_input_stream=IngestInputStream(
            input_id=s3_input.id,
            input_path=INPUT_PATH,
            selection_mode=StreamSelectionMode.AUDIO_RELATIVE,
            position=0
        )
    )

    video_input_stream = StreamInput(input_stream_id=video_ingest_input_stream.id)
    audio_input_stream = StreamInput(input_stream_id=audio_ingest_input_stream.id)

    # 4) Create Video Streams + Muxings
    sprite_created = False
    for video_profile in video_encoding_profiles:
        color_config = ColorConfig(
            copy_color_primaries_flag=True,
            copy_color_transfer_flag=True,
            copy_color_space_flag=True
        )

        # Configure advanced H.264 parameters (ref: https://developer.bitmovin.com/encoding/docs/h264-presets)
        if video_profile.get("profile") == ProfileH264.HIGH:
            adaptive_spatial_transform = True
            use_cabac = True
            num_refframe = 4
            num_bframe = 3
            weighted_prediction_p_frames = WeightedPredictionPFrames.SMART
        elif video_profile.get("profile") == ProfileH264.MAIN:
            adaptive_spatial_transform = False
            use_cabac = True
            num_refframe = 4
            num_bframe = 3
            weighted_prediction_p_frames = WeightedPredictionPFrames.SMART
        elif video_profile.get("profile") == ProfileH264.BASELINE:
            adaptive_spatial_transform = False
            use_cabac = False
            num_refframe = 4
            num_bframe = 0
            weighted_prediction_p_frames = WeightedPredictionPFrames.DISABLED
        else:
            raise Exception("Unknown profile. Valid profiles: HIGH, MAIN, BASELINE.")

        h264_codec = bitmovin_api.encoding.configurations.video.h264.create(
            h264_video_configuration=H264VideoConfiguration(
                name='Sample video codec configuration',
                height=video_profile.get("height"),
                bitrate=video_profile.get("bitrate"),
                max_bitrate=int(video_profile.get("bitrate") * 1.2),
                bufsize=int(video_profile.get("bitrate") * 1.5),
                profile=video_profile.get("profile"),
                level=video_profile.get("level"),
                min_keyframe_interval=2,
                max_keyframe_interval=2,
                color_config=color_config,
                ref_frames=num_refframe,
                bframes=num_bframe,
                cabac=use_cabac,
                adaptive_spatial_transform=adaptive_spatial_transform,
                weighted_prediction_p_frames=weighted_prediction_p_frames,
                preset_configuration=PresetConfiguration.VOD_HIGH_QUALITY
            )
        )

        h264_stream = bitmovin_api.encoding.encodings.streams.create(
            encoding_id=encoding.id,
            stream=Stream(
                codec_config_id=h264_codec.id,
                input_streams=[video_input_stream],
                name=f"Stream H264 {video_profile.get('height')}p",
                mode=video_profile.get('mode')
            )
        )

        # Create sprite/thumbnail generation on the highest resolution stream (1080p)
        if video_profile.get("height") == 1080 and not sprite_created:
            bitmovin_api.encoding.encodings.streams.sprites.create(
                encoding_id=encoding.id,
                stream_id=h264_stream.id,
                sprite=Sprite(
                    height=THUMBNAIL_HEIGHT,
                    width=THUMBNAIL_WIDTH,
                    unit=SpriteUnit.SECONDS,
                    distance=THUMBNAIL_INTERVAL_IN_SECONDS,
                    sprite_name=SPRITE_NAME,
                    vtt_name=SPRITE_VTT_NAME,
                    outputs=[EncodingOutput(
                        output_id=s3_output.id,
                        output_path=OUTPUT_BASE_PATH + "sprite/",
                        acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])],
                    h_tiles=SPRITE_HTILES_NUM,
                    v_tiles=SPRITE_VTILES_NUM,
                    jpeg_config=SpriteJpegConfig(quality=SPRITE_JPEG_QUALITY),
                    creation_mode=SpriteCreationMode.INTERVAL_START,
                    aspect_mode=ThumbnailAspectMode.STRETCH))
            sprite_created = True

        video_muxing_output = EncodingOutput(
            output_id=s3_output.id,
            output_path=f"{OUTPUT_BASE_PATH}video/{video_profile.get('height')}p",
            acl=[AclEntry(permission=AclPermission.PUBLIC_READ)]
        )

        bitmovin_api.encoding.encodings.muxings.fmp4.create(
            encoding_id=encoding.id,
            fmp4_muxing=Fmp4Muxing(
                segment_length=6,
                segment_naming='segment_%number%.m4s',
                init_segment_name='init.mp4',
                streams=[MuxingStream(stream_id=h264_stream.id)],
                outputs=[video_muxing_output],
                name=f"Video FMP4 Muxing {video_profile.get('height')}p"
            )
        )

    # 5) Create Audio Streams + Muxings
    for audio_profile in audio_encoding_profiles:
        aac_codec = bitmovin_api.encoding.configurations.audio.aac.create(
            aac_audio_configuration=AacAudioConfiguration(
                bitrate=audio_profile.get("bitrate"),
                rate=audio_profile.get("rate"),
                channel_layout=AacChannelLayout.CL_STEREO
            )
        )

        aac_stream = bitmovin_api.encoding.encodings.streams.create(
            encoding_id=encoding.id,
            stream=Stream(
                codec_config_id=aac_codec.id,
                input_streams=[audio_input_stream],
                name=f"Stream AAC {audio_profile.get('bitrate')/1000:.0f}kbps",
                mode=StreamMode.STANDARD
            )
        )

        audio_muxing_output = EncodingOutput(
            output_id=s3_output.id,
            output_path=f"{OUTPUT_BASE_PATH}audio/{audio_profile.get('bitrate')}",
            acl=[AclEntry(permission=AclPermission.PUBLIC_READ)]
        )

        bitmovin_api.encoding.encodings.muxings.fmp4.create(
            encoding_id=encoding.id,
            fmp4_muxing=Fmp4Muxing(
                segment_length=6,
                segment_naming='segment_%number%.m4s',
                init_segment_name='init.mp4',
                streams=[MuxingStream(stream_id=aac_stream.id)],
                outputs=[audio_muxing_output],
                name=f"Audio FMP4 Muxing {audio_profile.get('bitrate') / 1000:.0f}kbps"
            )
        )

    # 6) Start Encoding (no manifest in request)
    start_encoding_request = StartEncodingRequest()
    _execute_encoding(encoding=encoding, start_encoding_request=start_encoding_request)

    # 7) Create HLS/DASH manifests
    hls_manifest = _create_hls_manifest(encoding_id=encoding.id, output=s3_output, output_path=OUTPUT_BASE_PATH)
    dash_manifest = _create_dash_manifest(encoding_id=encoding.id, output=s3_output, output_path=OUTPUT_BASE_PATH)

    # 8) Generate HLS/DASH
    _execute_hls_manifest_generation(hls_manifest=hls_manifest)
    _execute_dash_manifest_generation(dash_manifest=dash_manifest)


def _execute_encoding(encoding, start_encoding_request):
    """
    Start the encoding process on Bitmovin and poll until it finishes or fails.
    """
    bitmovin_api.encoding.encodings.start(encoding_id=encoding.id, start_encoding_request=start_encoding_request)
    task = _wait_for_encoding_to_finish(encoding_id=encoding.id)

    while task.status not in [Status.FINISHED, Status.ERROR]:
        task = _wait_for_encoding_to_finish(encoding_id=encoding.id)

    if task.status == Status.ERROR:
        _log_task_errors(task)
        raise Exception("Encoding failed")

    print("Encoding finished successfully")


def _create_hls_manifest(encoding_id, output, output_path):
    """
    Create an HLS manifest from the generated FMP4 muxings.
    Loop through all FMP4 muxings and add audio or video entries to the HLS manifest.
    """
    manifest_output = EncodingOutput(
        output_id=output.id,
        output_path=output_path,
        acl=[AclEntry(permission=AclPermission.PUBLIC_READ)]
    )

    hls_manifest = bitmovin_api.encoding.manifests.hls.create(
        hls_manifest=HlsManifest(
            manifest_name='stream.m3u8',
            outputs=[manifest_output],
            name='HLS Manifest',
            hls_master_playlist_version=HlsVersion.HLS_V4,
            hls_media_playlist_version=HlsVersion.HLS_V4
        )
    )

    fmp4_muxings = bitmovin_api.encoding.encodings.muxings.fmp4.list(encoding_id=encoding_id)
    for muxing in fmp4_muxings.items:
        stream = bitmovin_api.encoding.encodings.streams.get(encoding_id=encoding_id, stream_id=muxing.streams[0].stream_id)
        if 'PER_TITLE_TEMPLATE' in stream.mode.value:
            continue

        codec = bitmovin_api.encoding.configurations.type.get(configuration_id=stream.codec_config_id)
        segment_path = _remove_output_base_path(muxing.outputs[0].output_path)

        if codec.type == CodecConfigType.AAC:
            # HLS audio
            audio_codec = bitmovin_api.encoding.configurations.audio.aac.get(configuration_id=stream.codec_config_id)
            bitmovin_api.encoding.manifests.hls.media.audio.create(
                manifest_id=hls_manifest.id,
                audio_media_info=AudioMediaInfo(
                    name='HLS Audio Media',
                    group_id='audio',
                    language='en',
                    segment_path=segment_path,
                    encoding_id=encoding_id,
                    stream_id=stream.id,
                    muxing_id=muxing.id,
                    uri=f'audio_{audio_codec.bitrate}.m3u8'
                )
            )
        elif codec.type == CodecConfigType.H264:
            # HLS video
            video_codec = bitmovin_api.encoding.configurations.video.h264.get(configuration_id=stream.codec_config_id)
            bitmovin_api.encoding.manifests.hls.streams.create(
                manifest_id=hls_manifest.id,
                stream_info=StreamInfo(
                    audio='audio',
                    closed_captions='NONE',
                    segment_path=segment_path,
                    uri=f'video_{video_codec.bitrate}.m3u8',
                    encoding_id=encoding_id,
                    stream_id=stream.id,
                    muxing_id=muxing.id
                )
            )

    return hls_manifest


def _create_dash_manifest(encoding_id, output, output_path):
    """
    Create a DASH manifest by creating a Period, adding Video/Audio Adaptation Sets,
    and attaching each FMP4 representation.
    """
    manifest_output = EncodingOutput(
        output_id=output.id,
        output_path=output_path,
        acl=[AclEntry(permission=AclPermission.PUBLIC_READ)]
    )

    dash_manifest = bitmovin_api.encoding.manifests.dash.create(
        dash_manifest=DashManifest(
            manifest_name='stream.mpd',
            outputs=[manifest_output],
            name='DASH Manifest'
        )
    )

    period = bitmovin_api.encoding.manifests.dash.periods.create(
        manifest_id=dash_manifest.id,
        period=Period()
    )

    video_adaptation_set = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.video.create(
        video_adaptation_set=VideoAdaptationSet(),
        manifest_id=dash_manifest.id,
        period_id=period.id
    )
    audio_adaptation_set = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.audio.create(
        audio_adaptation_set=AudioAdaptationSet(lang='en'),
        manifest_id=dash_manifest.id,
        period_id=period.id
    )

    fmp4_muxings = bitmovin_api.encoding.encodings.muxings.fmp4.list(encoding_id=encoding_id)
    for muxing in fmp4_muxings.items:
        stream = bitmovin_api.encoding.encodings.streams.get(encoding_id=encoding_id, stream_id=muxing.streams[0].stream_id)
        if 'PER_TITLE_TEMPLATE' in stream.mode.value:
            continue

        codec = bitmovin_api.encoding.configurations.type.get(configuration_id=stream.codec_config_id)
        segment_path = _remove_output_base_path(muxing.outputs[0].output_path)

        if codec.type == CodecConfigType.AAC:
            bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.create(
                manifest_id=dash_manifest.id,
                period_id=period.id,
                adaptationset_id=audio_adaptation_set.id,
                dash_fmp4_representation=DashFmp4Representation(
                    encoding_id=encoding_id,
                    muxing_id=muxing.id,
                    type_=DashRepresentationType.TEMPLATE,
                    mode=DashRepresentationTypeMode.TEMPLATE_REPRESENTATION,
                    segment_path=segment_path
                )
            )
        elif codec.type == CodecConfigType.H264:
            bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.create(
                manifest_id=dash_manifest.id,
                period_id=period.id,
                adaptationset_id=video_adaptation_set.id,
                dash_fmp4_representation=DashFmp4Representation(
                    encoding_id=encoding_id,
                    muxing_id=muxing.id,
                    type_=DashRepresentationType.TEMPLATE,
                    mode=DashRepresentationTypeMode.TEMPLATE_REPRESENTATION,
                    segment_path=segment_path
                )
            )

    return dash_manifest


def _execute_hls_manifest_generation(hls_manifest):
    """
    Start HLS manifest generation and poll until completed or fails.
    """
    bitmovin_api.encoding.manifests.hls.start(manifest_id=hls_manifest.id)
    task = _wait_for_hls_manifest_to_finish(manifest_id=hls_manifest.id)

    while task.status not in [Status.FINISHED, Status.ERROR]:
        task = _wait_for_hls_manifest_to_finish(manifest_id=hls_manifest.id)

    if task.status == Status.ERROR:
        _log_task_errors(task)
        raise Exception("HLS Manifest creation failed")

    print("HLS Manifest creation finished successfully")


def _execute_dash_manifest_generation(dash_manifest):
    """
    Start DASH manifest generation and poll until completed or fails.
    """
    bitmovin_api.encoding.manifests.dash.start(manifest_id=dash_manifest.id)
    task = _wait_for_dash_manifest_to_finish(manifest_id=dash_manifest.id)

    while task.status not in [Status.FINISHED, Status.ERROR]:
        task = _wait_for_dash_manifest_to_finish(manifest_id=dash_manifest.id)

    if task.status == Status.ERROR:
        _log_task_errors(task)
        raise Exception("DASH Manifest creation failed")

    print("DASH Manifest creation finished successfully")


def _wait_for_encoding_to_finish(encoding_id):
    """
    Poll encoding status every 5 seconds until finished or an error occurs.
    """
    time.sleep(5)
    task = bitmovin_api.encoding.encodings.status(encoding_id=encoding_id)
    print(f"Encoding status is {task.status} (progress: {task.progress} %)")
    return task


def _wait_for_hls_manifest_to_finish(manifest_id):
    """
    Poll HLS manifest creation status every 5 seconds until finished or an error occurs.
    """
    time.sleep(5)
    task = bitmovin_api.encoding.manifests.hls.status(manifest_id=manifest_id)
    print(f"HLS manifest status is {task.status} (progress: {task.progress} %)")
    return task


def _wait_for_dash_manifest_to_finish(manifest_id):
    """
    Poll DASH manifest creation status every 5 seconds until finished or an error occurs.
    """
    time.sleep(5)
    task = bitmovin_api.encoding.manifests.dash.status(manifest_id=manifest_id)
    print(f"DASH manifest status is {task.status} (progress: {task.progress} %)")
    return task


def _remove_output_base_path(text):
    """
    Remove the OUTPUT_BASE_PATH prefix from the given path to create a relative segment path.
    """
    if text.startswith(OUTPUT_BASE_PATH):
        return text[len(OUTPUT_BASE_PATH):]
    return text


def _log_task_errors(task):
    """
    Print error messages from the given task to the console.
    """
    if not task:
        return

    for message in filter(lambda m: m.type == MessageType.ERROR, task.messages):
        print(message.text)


if __name__ == '__main__':
    main()
