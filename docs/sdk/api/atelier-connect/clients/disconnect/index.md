# `atelier_connect::clients::disconnect`

Policy for disconnections

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::clients::disconnect`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/latest/atelier_connect/clients/disconnect/).

## Enums

| Item | Summary |
| --- | --- |
| [`DisconnectReason`](https://docs.rs/atelier-connect/latest/atelier_connect/clients/disconnect/enum.DisconnectReason.html) | Why a WebSocket connection terminated. |
| [`WssExitReason`](https://docs.rs/atelier-connect/latest/atelier_connect/clients/disconnect/enum.WssExitReason.html) | Why a WebSocket client's message loop exited. |

## Functions

| Item | Summary |
| --- | --- |
| [`classify_close_frame`](https://docs.rs/atelier-connect/latest/atelier_connect/clients/disconnect/fn.classify_close_frame.html) | Classify a WebSocket `CloseFrame` into a `DisconnectReason`. |
| [`classify_tungstenite_error`](https://docs.rs/atelier-connect/latest/atelier_connect/clients/disconnect/fn.classify_tungstenite_error.html) | Classify a raw `tungstenite::Error` into a `DisconnectReason`. |
