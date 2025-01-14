# bmenc
This repository contains sample code for using the [Bitmovin](https://bitmovin.com/) encoding API in both Python and Go. The examples are split into multiple categories:

- **basic**  
  Demonstrates basic encoding flows with minimal configurations.

- **subtitle**  
  Demonstrates how to add and manage subtitles or closed captions.

Prerequisites
- A Bitmovin API key. Sign up for one at Bitmovin if you don’t have it already.
- Appropriate language SDKs:
  - Bitmovin Python SDK

#### Quick Start
1. Clone this repository:
    ```
    git clone https://github.com/kazuhide/bmenc.git
    ```

2.	Install dependencies:
- For Python:
    ```
    cd bmenc/python
    pip install -r requirements.txt
    ```

2.	Set Environment Variables
    ```
    BITMOVIN_API_KEY: Your Bitmovin API key
    BITMOVIN_TENANT_ORG_ID: (If you want to use other org's plan)
    ```
