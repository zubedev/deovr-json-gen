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
DEFAULT_IGNORE_SIZE = 10  # in MB
DEFAULT_IGNORE_DURATION = 60  # in seconds

logging.basicConfig(format="%(asctime)s %(name)s %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


class MediaInfoDict(TypedDict):
    size: int  # in MB
    duration: int  # in seconds


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


def get_stereo_mode(path: Path) -> StereoMode:
    file_name = path.name.lower()
    if any([True for i in {"tb", "top-bottom", "over-under", "3dv"} if i in file_name]):
        return StereoMode.TOP_BOTTOM
    elif any([True for i in {"cuv", "custom_uv"} if i in file_name]):
        return StereoMode.CUSTOM_UV
    elif any([True for i in {"off", "2d", "mono", "single"} if i in file_name]):
        return StereoMode.MONOSCOPIC
    else:  # "sbs", "lr", "left-right", "side-by-side", "3dh"
        return StereoMode.SIDE_BY_SIDE


def get_screen_type(path: Path) -> ScreenType:
    file_name = path.name.lower()
    if any([True for i in {"rf52", "190", "fisheye190"} if i in file_name]):
        return ScreenType.FISHEYE_190
    elif any([True for i in {"mkx200", "200", "fisheye200"} if i in file_name]):
        return ScreenType.FISHEYE_200
    elif any([True for i in {"sphere", "360", "full"} if i in file_name]):
        return ScreenType.EQUIRECT_360
    elif any([True for i in {"fisheye"} if i in file_name]):
        return ScreenType.FISHEYE_180
    else:  # "dome", "180", "half"
        return ScreenType.EQUIRECT_180


def get_media_info(path: Path) -> MediaInfoDict:
    media_info = MediaInfo.parse(path)
    general_tracks = [t for t in media_info.tracks if t.track_type == "General"]
    if not general_tracks:
        return MediaInfoDict(size=0, duration=0)

    general_track = general_tracks[0]
    size_in_bytes = general_track.file_size or 0
    duration_in_ms = general_track.duration or 0

    size_in_mb = int(size_in_bytes / 1024 / 1024) if size_in_bytes else 0  # convert to MB
    duration_in_sec = int(duration_in_ms / 1000) if duration_in_ms else 0  # convert to seconds

    return MediaInfoDict(size=size_in_mb, duration=duration_in_sec)


def ignore_scene(media_info: MediaInfoDict, ignore_params: MediaInfoDict) -> bool:
    return media_info["size"] < ignore_params["size"] or media_info["duration"] < ignore_params["duration"]


def get_relative_path(path: Path, directory: Path) -> str:
    relative_path = path.relative_to(directory)
    return "/".join(relative_path.parts)


def get_video_url(path: Path, directory: Path, domain_url: str) -> str:
    return f"{domain_url}/{quote(get_relative_path(path, directory))}"


def get_scene(path: Path, directory: Path, domain_url: str, ignore_params: MediaInfoDict) -> Scene | None:
    media_info = get_media_info(path)

    if ignore_scene(media_info, ignore_params):
        log(f"Skipping {path} (size: {media_info['size']} MB, duration: {media_info['duration']} sec)", "debug")
        return None

    return Scene(
        title=path.stem,
        videoLength=media_info["duration"],
        thumbnailUrl="https://www.iconsdb.com/icons/preview/red/video-play-xxl.png",
        video_url=get_video_url(path, directory, domain_url),
        is3d=True,  # always true
        stereoMode=get_stereo_mode(path),
        screenType=get_screen_type(path),
    )


def get_scenes(files: list[Path], directory: Path, domain_url: str, ignore_params: MediaInfoDict) -> list[Scene]:
    scenes = []
    for f in files:
        scene = get_scene(f, directory, domain_url, ignore_params)
        if scene:
            scenes.append(scene)
    return scenes


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


def gen_json_file(scenes: Scenes, out_file: Path, indent: int = 4) -> None:
    with open(out_file, "w") as f:
        json.dump(scenes, f, indent=indent)


def parse_ignore_params(args: argparse.Namespace) -> MediaInfoDict:
    size: int | None = args.ignore_size
    if size is None:
        size = int(os.getenv(f"{ENV_PREFIX}IGNORE_SIZE", DEFAULT_IGNORE_SIZE))
    duration: int | None = args.ignore_duration
    if duration is None:
        duration = int(os.getenv(f"{ENV_PREFIX}IGNORE_DURATION", DEFAULT_IGNORE_DURATION))
    return MediaInfoDict(size=size, duration=duration)


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


def parse_domain_url(args: argparse.Namespace) -> str:
    # get domain url from command line arguments first
    # if no domain url were provided, try to get them from environment variables
    url: str = args.url

    if not url:
        url = os.getenv(f"{ENV_PREFIX}URL", "")

    # if no domain url were found, build from web server details
    if not url:
        ssl = strtobool(os.getenv("WEB_SSL"))
        protocol = "https" if ssl else "http"
        host = os.getenv("WEB_HOST", "localhost")
        port = os.getenv("WEB_PORT", "")  # 80/443 inferred from protocol
        url = f"{protocol}://{host}{':' if port else ''}{port}"

    return url


def parse_out_file(args: argparse.Namespace) -> Path:
    # get out file from command line arguments first
    # if no out file were provided, try to get them from environment variables
    out_file_str: str = args.out

    if not out_file_str:
        out_file_str = os.getenv(f"{ENV_PREFIX}OUT", "deovr")

    out_path = Path(out_file_str)

    # ensure out file is a file path and not a directory
    if out_path.is_dir():
        exit(f"ERROR: {out_path} is a directory, please provide a file path instead, i.e. {out_path / '<file_name>'}")

    # create parent directories if not exists
    if not out_path.parent.exists():
        out_path.parent.mkdir(parents=True, exist_ok=True)

    return out_path


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

    path = Path(path_str).resolve()

    # check path to directory is valid
    if not path.is_dir():
        exit(f"ERROR: {path} is not a valid directory")

    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="deovr-json-generator", description="DeoVR JSON Generator")

    parser.add_argument("dir", nargs="?", type=str, help="Path to directory with VR videos")
    parser.add_argument("--out", "-o", nargs="?", type=str, help="Output /path/file_name [default: deovr]")
    parser.add_argument("--url", "-u", nargs="?", type=str, help="Domain name of the web server")
    parser.add_argument("--ext", "-e", nargs="*", type=str, help="VR video file extensions")
    parser.add_argument("--loop", "-l", nargs="?", default=0, type=int, help="Generate every X seconds")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    ignore_size_help = "Ignore files smaller than X MB (megabytes) (set to 0 to disable) [default: 10]"
    parser.add_argument("--ignore-size", "-s", nargs="?", type=int, help=ignore_size_help)
    ignore_dur_help = "Ignore files smaller than X seconds (set to 0 to disable) [default: 60]"
    parser.add_argument("--ignore-duration", "-d", nargs="?", type=int, help=ignore_dur_help)

    return parser.parse_args()


def generate(args: argparse.Namespace, verbose: bool | None = None) -> None:
    log("Generating DeoVR JSON...", "info", verbose)

    directory = parse_directory(args)
    log(f"Directory: {directory}", "debug", verbose)

    out_file = parse_out_file(args)
    log(f"Output: {out_file}", "debug", verbose)

    url = parse_domain_url(args)
    log(f"Domain URL: {url}", "debug", verbose)

    extensions = parse_extensions(args)
    log(f"Extensions: {extensions}", "debug", verbose)

    ignore_params = parse_ignore_params(args)
    log(f"Ignore Params: {ignore_params}", "debug", verbose)

    files = sort_files(get_files(directory, extensions))
    print_files(files, verbose)

    scene_list = get_scenes(files, directory, url, ignore_params)
    library = Library(name="Library", list=scene_list)
    scenes = Scenes(scenes=[library])
    log(f"Scenes: {scenes}", "debug", verbose)

    gen_json_file(scenes, out_file)
    log("DeoVR JSON generated successfully!", "info", verbose)


if __name__ == "__main__":
    parsed_args = parse_args()
    verbose_logs = parsed_args.verbose or strtobool(os.getenv(f"{ENV_PREFIX}VERBOSE"))
    loop = parsed_args.loop or int(os.getenv(f"{ENV_PREFIX}LOOP", 0))

    while True:
        generate(parsed_args, verbose_logs)

        if not loop:
            log("Done!", "info", verbose_logs)
            break

        log(f"Sleeping for {loop} seconds ...", "info", verbose_logs)
        time.sleep(loop)
