---
title: Audio, codecs & transcription
description: Understand Studio audio routes, DAC and AudioTools requirements, the pure-Python protobuf artifact, and the limits of audio qualification.
---

Audio support is a collection of backend-specific paths: codec encode/decode, speech generation, transcription, dataset decoding, and model training. Installing one codec does not qualify every audio model.

## Select the right runtime

Studio exposes audio generation, speech, and transcription operations through its inference routes. Native transcription helpers and Torch-backed model paths have different dependencies. The model's requirements, sample rate, device support, checkpoint availability, and input format still matter.

For a first test, use a short, authorized audio clip, verify that it decodes correctly, and inspect generated output before attempting large datasets or long recordings. For training, preserve the expected sampling/channel conventions and read [dataset preparation](datasets.md).

## The compatibility exception is intentional

The shared ML environment uses:

| Component | Selected artifact |
| --- | --- |
| Descript Audio Codec | `descript-audio-codec==1.0.0` |
| AudioTools | Stable upstream **0.7.4** checksum-qualified GitHub archive |
| Protobuf | Official pure-Python **4.25.9** wheel |
| TensorBoard | **2.20.0** |
| TorchAudio | **2.11.0**, with the matching Torch backend suffix |
| TorchCodec | **0.16.0**, where the platform contract permits |

AudioTools 0.7.4 is newer than the 0.7.2 package on PyPI but still requires protobuf below 5. TensorBoard 2.21 instead requires protobuf 6. The selected versions honor both packages' real requirements.

The protobuf 4 native abi3 wheel raises a CPython 3.14 metaclass error. The pure wheel's exact URL and SHA-256 are mandatory; setting a Python-implementation environment variable alone does not prevent the selector's native-extension probe. See the [artifact matrix](dependency-matrix.md) rather than substituting another wheel with the same version.

## What has been exercised

The Windows migration exercised real DAC encode/decode and checkpoint paths, plus TensorBoard event write/read in tiny-model training. That is evidence for those paths, not all speech architectures, all quantization modes, or macOS/Linux runtime certification.

Old fixed-Transformers sidecar environments are retired/ignored in this migration; old user directories are not deleted as a cleanup shortcut.

## Troubleshooting audio independently

- A codec import failure may be a shared dependency/artifact mismatch, not a corrupt audio file.
- A decode error may involve the container, sample rate, or platform decoder.
- A missing checkpoint is not solved by changing Torch versions.
- A device-specific model error must be investigated on that exact backend.
- A GGUF-only environment does not include Python Torch codecs just because Studio's HTTP routes exist.

Record the model, codec, input properties, platform, and sanitized error. Keep voices and recordings out of public bug reports unless you have permission to share them.

**Sources:** [audio requirements](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/requirements/extras.txt), [archive pins](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/requirements/extras-no-deps.txt), [codec runtime](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/core/inference/audio_codecs.py), [inference routes](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/routes/inference.py).
