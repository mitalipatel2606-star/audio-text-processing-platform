#!/bin/bash
echo "Hello World" | piper --model en_US-amy-medium.onnx --output_file test.wav
echo "Generated test.wav successfully."
