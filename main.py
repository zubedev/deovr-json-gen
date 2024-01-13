import argparse
import enum
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, NotRequired, TypedDict
from urllib.parse import quote

from pymediainfo import MediaInfo

ENV_PREFIX = "DEOVR_JSON_GEN_"

DEFAULT_EXTENSIONS = {"mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "mpg", "mpeg", "m2v", "ts"}

logging.basicConfig(format="%(asctime)s %(name)s %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


class StereoMode(enum.StrEnum):
    MONOSCOPIC = "off"
    SIDE_BY_SIDE = "sbs"
    TOP_BOTTOM = "tb"
    CUSTOM_UV = "cuv"


class ScreenType(enum.StrEnum):
    FLAT = "flat"
    EQUIRECT_180 = "dome"
    EQUIRECT_360 = "sphere"
    FISHEYE_180 = "fisheye"
    FISHEYE_190 = "rf52"
    FISHEYE_200 = "mkx200"


# https://deovr.com/app/doc#multiple-videos-deeplink
class Scene(TypedDict):
    id: NotRequired[int]
    title: str
    videoLength: int  # in seconds
    video_url: str  # required atm but could be set optional if encodings are used instead
    thumbnailUrl: str
    is3d: bool  # always true
    stereoMode: StereoMode
    screenType: ScreenType
    encodings: NotRequired[list[dict[str, Any]]]  # either encodings or video_url
    videoThumbnail: NotRequired[str]  # url
    videoPreview: NotRequired[str]  # url
    corrections: NotRequired[dict[str, int | float]]
    timeStamps: NotRequired[list[dict[str, Any]]]
    skipIntro: NotRequired[int]  # in seconds
    path: NotRequired[str]  # only for images mode


class Library(TypedDict):
    name: str
    list: list[Scene]


class Scenes(TypedDict):
    scenes: list[Library]


def log(message: str, level: str = "info", printout: bool | None = False) -> None:
    getattr(logger, level)(message)
    if printout:
        print(message, flush=True)


def strtobool(value: Any) -> bool | None:
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = str(value).lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        return None


def get_video_length(path: Path) -> int:
    media_info = MediaInfo.parse(path)
    general_tracks = [t for t in media_info.tracks if t.track_type == "General"]
    if not general_tracks:
        return 0

    general_track = general_tracks[0]
    duration_in_ms = general_track.duration
    if not duration_in_ms:
        return 0

    return int(duration_in_ms / 1000)  # convert to seconds


def get_video_url(path: Path) -> str:
    url = os.getenv(f"{ENV_PREFIX}URL", "")

    if not url:
        ssl = strtobool(os.getenv("WEB_SSL"))
        protocol = "https" if ssl else "http"
        host = os.getenv("WEB_HOST", "localhost")
        port = os.getenv("WEB_PORT", "")  # 80/443 inferred from protocol
        url = f"{protocol}://{host}{':' if port else ''}{port}"

    return f"{url}/{quote(str(path.name))}"


def get_scene(path: Path) -> Scene:
    return Scene(
        title=path.stem,
        videoLength=get_video_length(path),
        thumbnailUrl="https://www.iconsdb.com/icons/preview/red/video-play-xxl.png",
        video_url=get_video_url(path),
        is3d=True,
        stereoMode=StereoMode.SIDE_BY_SIDE,
        screenType=ScreenType.EQUIRECT_180,
    )


def sort_files(files: list[Path]) -> list[Path]:
    return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)


def print_files(paths: list[Path], verbose: bool | None = False) -> None:
    for p in paths:
        log(f"+ {p}", "debug", verbose)


def get_files(path: Path, ext: set[str] | None = None) -> list[Path]:
    if ext is None:
        ext = DEFAULT_EXTENSIONS

    files: list[Path] = []
    for e in ext:
        files.extend(path.rglob(f"*.{e}"))

    return files


def parse_extensions(args: argparse.Namespace) -> set[str]:
    # get extensions from command line arguments first
    ext = set(args.ext) if args.ext else set()

    # if no extensions were provided, try to get them from environment variables
    if not ext:
        ext_str = os.getenv(f"{ENV_PREFIX}EXT")
        ext_list = ext_str.split(",") if ext_str else []
        ext = {e.strip() for e in ext_list}

    # if no extensions were found, use default extensions
    if not ext:
        ext = DEFAULT_EXTENSIONS

    return ext


def parse_directory(args: argparse.Namespace) -> Path:
    # get directory from command line arguments first
    # if no directory were provided, try to get them from environment variables
    path_str = args.dir

    if not path_str:
        dirs_str = os.getenv(f"{ENV_PREFIX}DIR")
        path_str = dirs_str.strip() if dirs_str else ""

    # if no directory were found, raise an error and exit
    if not path_str:
        exit("ERROR: No path or directory were provided")

    path = Path(path_str)

    # check path to directory is valid
    if not path.is_dir():
        exit(f"ERROR: {path} is not a valid directory")

    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="deovr-json-generator", description="DeoVR JSON Generator")
    parser.add_argument("dir", nargs="?", type=str, help="Path to directory with VR videos")
    parser.add_argument("--ext", "-e", nargs="*", type=str, help="VR video file extensions")
    parser.add_argument("--loop", "-l", nargs="?", default=0, type=int, help="Generate every X seconds")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    return parser.parse_args()


def generate(args: argparse.Namespace, verbose: bool | None = None) -> None:
    log("Generating DeoVR JSON...", "info", verbose)

    directory = parse_directory(args)
    log(f"Directory: {directory}", "debug", verbose)

    extensions = parse_extensions(args)
    log(f"Extensions: {extensions}", "debug", verbose)

    files = sort_files(get_files(directory, extensions))
    print_files(files, verbose)

    scene_list = []
    for f in files:
        scene_list.append(get_scene(f))

    library = Library(name="Library", list=scene_list)
    scenes = Scenes(scenes=[library])
    log(f"Scenes: {scenes}", "debug", verbose)

    with open("deovr", "w") as file:
        json.dump(scenes, file, indent=4)
    log("DeoVR JSON generated successfully!", "info", verbose)


if __name__ == "__main__":
    args = parse_args()
    verbose = args.verbose or strtobool(os.getenv(f"{ENV_PREFIX}VERBOSE"))
    loop = args.loop or int(os.getenv(f"{ENV_PREFIX}LOOP", 0))

    while True:
        generate(args, verbose)

        if not loop:
            log("Done!", "info", verbose)
            break

        log(f"Sleeping for {loop} seconds ...", "info", verbose)
        time.sleep(loop)
