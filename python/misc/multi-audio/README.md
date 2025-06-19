# マルチオーディオ HLS/DASH エンコーディング

このサンプルコードは、Bitmovin API を使用して複数音声を含むマルチオーディオの HLS/DASH 配信を実現する方法を示しています。

## 概要

このディレクトリには2つのマルチオーディオエンコーディングサンプルが含まれています：

### 1. `create_multi_audio_h264_aac_fmp4_hls_dash.py`
FMP4形式でHLS/DASHの両方を生成します。モダンなプレイヤーに最適です。

### 2. `create_multi_audio_h264_aac_ts_hls_fmp4_dash.py`
HLSはTS形式、DASHはFMP4形式で生成します。レガシーデバイスとの互換性が必要な場合に使用します。

両スクリプトとも以下の処理を行います：

1. 2つの入力ファイルから映像と音声を抽出
   - `INPUT_PATH_1`: メイン動画 + 主音声
   - `INPUT_PATH_2`: メイン動画 + 副音声（解説音声など）
2. H.264でマルチビットレートの映像をエンコード
3. AACで主音声・副音声をエンコード
4. HLS/DASHマニフェストを生成し、音声切り替え可能な配信を実現

## 主な特徴

### 複数ファイルからの入力処理

`IngestInputStream` クラスを使用することで、複数のファイルから必要なストリームを柔軟に抽出できます：

```python
# ビデオストリームの抽出（1つ目のファイルから）※2つ目のファイルも同じ動画であるなら INPUT_PATH_1/INPUT_PATH_2 どちらを指定しても良い。
video_ingest_input_stream = IngestInputStream(
    input_id=s3_input.id,
    input_path=INPUT_PATH_1,
    selection_mode=StreamSelectionMode.VIDEO_RELATIVE,
    position=0  # ファイル内の最初のビデオストリーム
)

# 主音声の抽出（1つ目のファイルから）
audio_ingest_input_stream_1 = IngestInputStream(
    input_id=s3_input.id,
    input_path=INPUT_PATH_1,
    selection_mode=StreamSelectionMode.AUDIO_RELATIVE,
    position=0  # ファイル内の最初のオーディオストリーム
)

# 副音声の抽出（2つ目のファイルから）
audio_ingest_input_stream_2 = IngestInputStream(
    input_id=s3_input.id,
    input_path=INPUT_PATH_2,
    selection_mode=StreamSelectionMode.AUDIO_RELATIVE,
    position=0  # ファイル内の最初のオーディオストリーム
)
```

ファイル数がいくつ増えても、ファイルパスとポジションを指定することで対応可能です。さらに高度な処理として、Bitmovinは以下などの入力ファイルの処理もサポートしています：
- **Concatenation**: 複数のファイルを連結（クラス名：ConcatenationInputStream）
- **AudioMix**: 複数の音声トラックをミックス（クラス名：AudioMixInputStream）
- **Trimming（時間指定）**: 入力ファイルの時間指定でのトリミング（クラス名：TimeBasedTrimmingInputStream）
- **Trimming（タイムコード指定）**: 入力ファイルのタイムコード指定でのトリミング（クラス名：TimecodeTrackTrimmingInputStream）

### HLS/DASH でのマルチオーディオ実装

異なる音声トラックは**別々のMuxing**として処理し、それぞれをマニフェストに含めます：

```python
# 主音声用のMuxing
audio_muxing_output_main = EncodingOutput(
    output_path=f"{OUTPUT_BASE_PATH}audio/main/{bitrate}"
)

# 副音声用のMuxing
audio_muxing_output_commentary = EncodingOutput(
    output_path=f"{OUTPUT_BASE_PATH}audio/commentary/{bitrate}"
)
```

### HLS の音声設定

HLSでは `EXT-X-MEDIA` タグを使用して複数の音声トラックを定義します。重要な属性：

| 属性 | 説明 | 例                       |
|------|------|-------------------------|
| **NAME** | 表示名 | '主音声', '副音声'            |
| **LANGUAGE** | 言語コード | 'ja', 'en'              |
| **GROUP-ID** | オーディオグループ識別子 | 'AUDIO_AAC'             |
| **DEFAULT** | デフォルト選択 | true (主音声), false (副音声) |
| **AUTOSELECT** | 自動選択 | true, false             |

```python
AudioMediaInfo(
    name='主音声',
    group_id='AUDIO_AAC',
    language='ja',
    is_default=True,
    autoselect=True
)
```

### オーディオグループIDの使い分け

このサンプルでは単一の `AUDIO_AAC` グループIDを使用していますが、以下の場合は異なるグループIDを使用することを推奨します：

- **異なるコーデック**: AAC vs Dolby Digital → 別グループID
- **異なるチャンネルレイアウト**: ステレオ vs 5.1ch → 別グループID  
- **異なるサンプルレート**: 48kHz vs 44.1kHz → 別グループID

同じコーデック・仕様で異なるビットレートの場合は、同じグループID内でアダプティブ切り替えが可能です。

### DASH での言語ラベル設定

DASHでは `Label` 要素を使用して、各 `AdaptationSet` に言語やトラックタイプのラベルを付与できます：

```python
# 主音声用のAdaptationSet
AudioAdaptationSet(
    lang='en',
    labels=[Label(value='主音声')]
)

# 副音声用のAdaptationSet
AudioAdaptationSet(
    lang='en',
    labels=[Label(value='副音声')]
)
```

## 多言語対応への応用

このサンプルは主音声・副音声の実装例ですが、多言語音声（英語・日本語など）にも同じアプローチが適用できます：

1. 各言語の音声ファイルを `IngestInputStream` で指定
2. 適切な `language` 属性を設定（'en', 'ja' など）
3. `NAME` や `Label` で言語を明示
4. 必要に応じて `DEFAULT` と `AUTOSELECT` を調整

## 使用方法

1. API認証情報とS3バケット情報を設定
2. 入力ファイルパスを指定：
   - `INPUT_PATH_1`: メイン動画 + 主音声
   - `INPUT_PATH_2`: メイン動画 + 副音声
3. スクリプトを実行

```bash
# FMP4形式のHLS/DASH
python create_multi_audio_h264_aac_fmp4_hls_dash.py

# TS形式のHLS + FMP4形式のDASH
python create_multi_audio_h264_aac_ts_hls_fmp4_dash.py
```

## テストファイルについて

このサンプルで使用している `test5.mkv` は、[IETF の Matroska テストファイルリポジトリ](https://github.com/ietf-wg-cellar/matroska-test-files)で公開されている「5. Multiple audio/subtitles」のテストファイルです。

この動画には複数の音声トラックが1つのMKVファイルに含まれているため、以下のFFmpegコマンドで動画+主音声と動画+副音声の2つのファイルに分割して使用しています：

```bash
# 動画 + 主音声（1番目の音声トラック）を抽出
ffmpeg -i test5.mkv -map 0:v -map 0:a:0 -c copy test5_main.mkv

# 動画 + 副音声（2番目の音声トラック）を抽出
ffmpeg -i test5.mkv -map 0:v -map 0:a:1 -c copy test5_commentary.mkv
```

- `-map 0:v`: すべてのビデオストリームをコピー
- `-map 0:a:0`: 1番目の音声トラック（主音声）を選択
- `-map 0:a:1`: 2番目の音声トラック（副音声）を選択
- `-c copy`: 再エンコードせずにストリームをコピー

## 出力構造

### FMP4形式（create_multi_audio_h264_aac_fmp4_hls_dash.py）
```
output/
├── video/           # 映像セグメント
│   ├── 240p/
│   ├── 360p/
│   ├── 480p/
│   ├── 720p/
│   └── 1080p/
├── audio/           # 音声セグメント
│   ├── main/        # 主音声
│   │   └── 128000/
│   └── commentary/  # 副音声
│       └── 128000/
├── stream.m3u8      # HLSマスタープレイリスト
└── stream.mpd       # DASHマニフェスト
```

### TS/FMP4混在形式（create_multi_audio_h264_aac_ts_hls_fmp4_dash.py）
```
output/
├── video/
│   ├── fmp4/        # DASH用映像セグメント（FMP4）
│   │   ├── 240p/
│   │   ├── 360p/
│   │   └── ...
│   └── ts/          # HLS用映像セグメント（TS）
│       ├── 240p/
│       ├── 360p/
│       └── ...
├── audio/
│   ├── fmp4/        # DASH用音声セグメント（FMP4）
│   │   ├── main/
│   │   └── commentary/
│   └── ts/          # HLS用音声セグメント（TS）
│       ├── main/
│       └── commentary/
├── stream.m3u8      # HLSマスタープレイリスト（TSセグメント参照）
└── stream.mpd       # DASHマニフェスト（FMP4セグメント参照）
```

## 注意事項

- 音声トラックの言語設定は配信コンテンツに合わせて適切に設定してください
- プレイヤーの互換性を考慮し、`DEFAULT` と `AUTOSELECT` （または `FORCED`）の組み合わせを検討してください
- 異なる仕様の音声を追加する場合は、適切なグループIDの分離を行ってください
- TS/FMP4混在形式ではストレージ使用量が約2倍になることに注意してください