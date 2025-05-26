# OBS Object Detection
A simple Python program that can add YOLO object detection to OBS using OBS websockets.

## Setup
You need to have uv and Python 3.9 or newer. Start by installing dependencies
```shell
uv sync
```
Then you can run the program after setting up your config file by running
```shell
uv run src/main.py
```

> [!NOTE]  
> Docker images are planned for a future release.

### Camera Number Selection
Currently, there is no simple way to find the number for the camera that you want to use, so the process mostly just boils down to trial and error.
Start with zero and work your way up until you find the correct camera.

### Config
You can write a configuration file based on the example config file, then rename it to `obs-object-detection-cfg.ini`.

## Support
If you have any issues, just add an issue on the GitHub page.

## Future Plans
Planned features for the future
- [x] Configurable Object Detections
- [ ] Configuration Generator
- [ ] Docker image for server
- [ ] Face blurring

## Contribution
Contributions are greatly welcome. Just make a pull request for any issue that you may want to resolve.
Feel free to add an issue or discussion if you have any questions or comments.

## License
This software is published under the Mozilla Public License 2.0. Please see `LICENSE` for more details.
