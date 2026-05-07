import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
import xml.etree.ElementTree as ET

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText


LANGUAGE_OPTIONS = [
    "Japanese (jpn)",
    "English (eng)",
    "German (deu)",
    "French (fra)",
    "Italian (ita)",
    "Korean (kor)",
    "Russian (rus)",
    "Spanish (spa)",
    "Chinese (zho)",
    "Foreign language (mul)",
]

GENRE_OPTIONS = [
    "News / Reports (0x0/0x0)",
    "Sports (0x1/0x0)",
    "Information / Wide Show (0x2/0x0)",
    "Drama (0x3/0x0)",
    "Music (0x4/0x0)",
    "Variety (0x5/0x0)",
    "Movie (0x6/0x0)",
    "Animation / Special Effects (0x7/0x0)",
    "Documentary / Culture (0x8/0x0)",
    "Theater / Performance (0x9/0x0)",
    "Hobby / Education (0xA/0x0)",
    "Welfare (0xB/0x0)",
    "Others (0xF/0x0)",
]

AUDIO_BITRATES = ["32k", "48k", "64k", "96k", "128k", "160k", "192k", "224k", "256k", "320k"]


AUDIO_FILE_PATTERN = (
    "*.wav *.wave *.flac *.aiff *.aif *.aifc "
    "*.mp3 *.m4a *.aac *.adts *.ac3 *.eac3 "
    "*.ogg *.oga *.opus *.wma *.alac *.caf "
    "*.mka *.webm *.mp4 *.mov"
)


def app_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def default_lang_dir():
    # Keep language JSON files next to the app:
    #   MakeTS/lang/en.json
    #   MakeTS/lang/ja.json
    return app_base_dir() / "lang"


def default_exe_dir():
    # Keep external executables next to the app:
    #   MakeTS/exe_files/ffmpeg.exe
    #   MakeTS/exe_files/ffprobe.exe
    #   MakeTS/exe_files/tsp.exe
    return app_base_dir() / "exe_files"


def exe_name(name):
    return f"{name}.exe" if os.name == "nt" else name


def default_ffmpeg_path():
    return default_exe_dir() / exe_name("ffmpeg")


def default_tsp_path():
    return default_exe_dir() / exe_name("tsp")


UI_TEXT_KEYS = [
    "UI Language",
    "Input / Output",
    "Files",
    "Add",
    "Clear",
    "Video",
    "Audio",
    "TS Info",
    "Program",
    "Log",
    "Encode",
    "Stop",
    "Ready",
    "Encoding",
    "ffmpeg",
    "Output",
    "Save as",
    "Output file name",
    "Browse",
    "Size",
    "Scan",
    "Aspect",
    "Bitrate",
    "Maxrate",
    "Bufsize",
    "GOP",
    "Primary Audio",
    "Use input audio",
    "Audio file",
    "Mode",
    "Sample rate",
    "Language",
    "Track name",
    "Secondary Audio",
    "WAV",
    "NIT / Station Profile",
    "Inject TS information with TSDuck",
    "Network Name",
    "TS Name",
    "Provider",
    "Service Base",
    "Service ID",
    "OneSeg Service ID",
    "TS ID",
    "Original NW ID",
    "Network ID",
    "Remote Key ID",
    "Service Type",
    "Import",
    "Import NIT",
    "Export",
    "Export NIT",
    "Physical Channels",
    "Relay Station",
    "SDT / Service Names",
    "Import SDT",
    "Export SDT",
    "Service 1",
    "Service 2",
    "Service 3",
    "OneSeg",
    "CAT / Access Control",
    "Inject CAT",
    "Import CAT",
    "Export CAT",
    "CAT Version",
    "CA System ID",
    "Transmission Type",
    "EMM PID",
    "Private Data",
    "EIT Present Event",
    "Inject EIT",
    "Event ID",
    "Event Name",
    "Description",
    "Start Time",
    "Duration",
    "Running Status",
    "Genre",
    "TOT",
    "Inject TOT",
    "Time Source",
    "Manual Time",
    "Cut",
    "Copy",
    "Paste",
    "Select All",
    "Select ffmpeg.exe",
    "Select tsp.exe",
    "Select primary audio file",
    "Select secondary audio WAV",
    "Select secondary audio file",
    "Select output folder",
    "Select files",
    "No input",
    "No output",
    "Add files first.",
    "Select output folder.",
    "Stop requested",
    "ffmpeg, ffprobe, or tsp was not found. Check paths.",
    "TSDuck XML",
    "All files",
    "MPEG2-TS files",
    "Audio files",
    "Video files",
    "WAV files"
]

BUILTIN_JA_TRANSLATIONS = {
    "UI Language": "表示言語",
    "Input / Output": "入力 / 出力",
    "Files": "ファイル",
    "Add": "追加",
    "Clear": "クリア",
    "Video": "映像",
    "Audio": "音声",
    "TS Info": "TS情報",
    "Program": "番組情報",
    "Log": "ログ",
    "Encode": "出力",
    "Stop": "停止",
    "Ready": "待機中",
    "Encoding": "エンコード中",
    "ffmpeg": "ffmpeg",
    "Output": "出力先",
    "Save as": "名前を付けて保存",
    "Output file name": "保存ファイル名",
    "Browse": "参照",
    "Size": "サイズ",
    "Scan": "走査方式",
    "Aspect": "アスペクト",
    "Bitrate": "ビットレート",
    "Maxrate": "最大レート",
    "Bufsize": "バッファサイズ",
    "GOP": "GOP",
    "Primary Audio": "主音声",
    "Use input audio": "入力音声を使う",
    "Audio file": "音声ファイル",
    "Mode": "形式",
    "Sample rate": "サンプルレート",
    "Language": "言語",
    "Track name": "トラック名",
    "Secondary Audio": "副音声",
    "WAV": "WAV",
    "NIT / Station Profile": "NIT / 放送局情報",
    "Inject TS information with TSDuck": "TSDuckでTS情報を注入",
    "Network Name": "ネットワーク名",
    "TS Name": "TS名",
    "Provider": "提供者",
    "Service Base": "サービス名ベース",
    "Service ID": "サービスID",
    "OneSeg Service ID": "ワンセグサービスID",
    "TS ID": "TS ID",
    "Original NW ID": "Original NW ID",
    "Network ID": "ネットワークID",
    "Remote Key ID": "リモコンキーID",
    "Service Type": "サービス種別",
    "Import": "インポート",
    "Import NIT": "NITインポート",
    "Export": "エクスポート",
    "Export NIT": "NITエクスポート",
    "Physical Channels": "物理チャンネル",
    "Relay Station": "中継局",
    "SDT / Service Names": "SDT / サービス名",
    "Import SDT": "SDTインポート",
    "Export SDT": "SDTエクスポート",
    "Service 1": "サービス1",
    "Service 2": "サービス2",
    "Service 3": "サービス3",
    "OneSeg": "ワンセグ",
    "CAT / Access Control": "CAT / アクセス制御",
    "Inject CAT": "CATを注入",
    "Import CAT": "CATインポート",
    "Export CAT": "CATエクスポート",
    "CAT Version": "CATバージョン",
    "CA System ID": "CAシステムID",
    "Transmission Type": "伝送種別",
    "EMM PID": "EMM PID",
    "Private Data": "プライベートデータ",
    "EIT Present Event": "EIT 現在番組",
    "Inject EIT": "EITを注入",
    "Event ID": "イベントID",
    "Event Name": "番組名",
    "Description": "説明",
    "Start Time": "開始時刻",
    "Duration": "長さ",
    "Running Status": "実行状態",
    "Genre": "ジャンル",
    "TOT": "TOT",
    "Inject TOT": "TOTを注入",
    "Time Source": "時刻ソース",
    "Manual Time": "手動時刻",
    "Cut": "切り取り",
    "Copy": "コピー",
    "Paste": "貼り付け",
    "Select All": "すべて選択",
    "Select ffmpeg.exe": "ffmpeg.exeを選択",
    "Select tsp.exe": "tsp.exeを選択",
    "Select primary audio file": "主音声ファイルを選択",
    "Select secondary audio WAV": "副音声WAVを選択",
    "Select secondary audio file": "副音声ファイルを選択",
    "Select output folder": "出力フォルダーを選択",
    "Select files": "ファイルを選択",
    "No input": "入力なし",
    "No output": "出力先なし",
    "Add files first.": "先にファイルを追加してください。",
    "Select output folder.": "出力フォルダーを選択してください。",
    "Stop requested": "停止要求",
    "ffmpeg, ffprobe, or tsp was not found. Check paths.": "ffmpeg、ffprobe、またはtspが見つかりません。パスを確認してください。",
    "TSDuck XML": "TSDuck XML",
    "All files": "すべてのファイル",
    "MPEG2-TS files": "MPEG2-TSファイル",
    "Audio files": "音声ファイル",
    "Video files": "映像ファイル",
    "WAV files": "WAVファイル"
}


def make_language_pack(code, name, translations):
    return {
        "language_code": code,
        "language_name": name,
        "translations": translations,
    }


def default_language_packs():
    return {
        "en": make_language_pack("en", "English", {key: key for key in UI_TEXT_KEYS}),
        "ja": make_language_pack("ja", "Japanese", BUILTIN_JA_TRANSLATIONS.copy()),
    }



class MakeTSGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MakeTS GUI")
        self.geometry("940x780")
        self.minsize(840, 700)

        self.input_files = []
        self.process = None
        self.worker_thread = None
        self.log_queue = queue.Queue()
        self.secondary_audio_controls = []
        self.description_text = None

        self.init_vars()
        self.bind_var_events()
        self.build_ui()
        self.after(100, self.poll_log_queue)

    # ------------------------------------------------------------------ setup

    def init_vars(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.lang_dir = default_lang_dir()
        self.language_packs = self.load_language_packs()
        self.language_names = self.language_display_names()
        self.ui_language = tk.StringVar(value=self.default_language_name())

        self.ffmpeg_path = tk.StringVar(value=str(default_ffmpeg_path()))
        self.output_path = tk.StringVar(value="")

        self.video_size = tk.StringVar(value="1440x1080")
        self.scan_mode = tk.StringVar(value="60i")
        self.output_aspect = tk.StringVar(value="16:9")
        self.video_bitrate = tk.StringVar(value="13M")
        self.video_maxrate = tk.StringVar(value="14M")
        self.video_bufsize = tk.StringVar(value="8M")
        self.gop = tk.StringVar(value="15")

        self.primary_use_input_audio = tk.StringVar(value="on")
        self.primary_audio_path = tk.StringVar(value="")
        self.primary_audio_language = tk.StringVar(value="Japanese (jpn)")
        self.primary_audio_title = tk.StringVar(value="日本語")
        self.audio_mode = tk.StringVar(value="Stereo")
        self.audio_bitrate = tk.StringVar(value="256k")
        self.audio_samplerate = tk.StringVar(value="48000")

        self.secondary_audio_path = tk.StringVar(value="")
        self.secondary_audio_mode = tk.StringVar(value="Stereo")
        self.secondary_audio_bitrate = tk.StringVar(value="256k")
        self.secondary_audio_samplerate = tk.StringVar(value="48000")
        self.secondary_audio_language = tk.StringVar(value="English (eng)")
        self.secondary_audio_title = tk.StringVar(value="英語")

        self.ts_info_enabled = tk.StringVar(value="on")
        self.tsduck_path = tk.StringVar(value=str(default_tsp_path()))

        self.provider_name = tk.StringVar(value="ＳＢＨ")
        self.network_name = tk.StringVar(value="茨城７")
        self.ts_name = tk.StringVar(value="ＳＢＨ筑波")
        self.service_name = tk.StringVar(value="ＳＢＨ筑波")
        self.service_name_1 = tk.StringVar(value="ＳＢＨ筑波・１")
        self.service_name_2 = tk.StringVar(value="ＳＢＨ筑波・２")
        self.service_name_3 = tk.StringVar(value="ＳＢＨ筑波・３")
        self.service_name_1seg = tk.StringVar(value="ＳＢＨ筑波携帯１")

        self.service_id = tk.StringVar(value="0x6238")
        self.oneseg_service_id = tk.StringVar(value="0x63B8")
        self.transport_stream_id = tk.StringVar(value="0x7E57")
        self.original_network_id = tk.StringVar(value="0x7E57")
        self.network_id = tk.StringVar(value="0x7E57")
        self.remote_control_key_id = tk.StringVar(value="0x11")
        self.service_type = tk.StringVar(value="0x01")

        self.cat_enabled = tk.StringVar(value="on")
        self.cat_version = tk.StringVar(value="11")
        self.cat_ca_system_id = tk.StringVar(value="0x000E")
        self.cat_transmission_type = tk.StringVar(value="7")
        self.cat_pid = tk.StringVar(value="0x0070")
        self.cat_private_data = tk.StringVar(value="01")

        self.physical_channels = [
            tk.StringVar(value=value)
            for value in ("15", "40", "45", "", "", "", "", "", "", "")
        ]

        self.eit_enabled = tk.StringVar(value="on")
        self.event_id = tk.StringVar(value="0x0001")
        self.event_name = tk.StringVar(value="おはよう天気")
        self.event_text = tk.StringVar(value="天気情報")
        self.event_start_time = tk.StringVar(value="2026-03-30 05:00:00")
        self.event_duration = tk.StringVar(value="00:15:00")
        self.event_language = tk.StringVar(value="Japanese (jpn)")
        self.event_running_status = tk.StringVar(value="running")
        self.genre = tk.StringVar(value="News / Reports (0x0/0x0)")

        self.tot_enabled = tk.StringVar(value="on")
        self.tot_time_source = tk.StringVar(value="manual")
        self.tot_start_time = tk.StringVar(value="2026-03-30 05:00:00")

    def bind_var_events(self):
        self.ui_language.trace_add("write", self.on_ui_language_changed)
        self.video_size.trace_add("write", self.on_video_size_changed)
        self.audio_mode.trace_add("write", self.on_audio_mode_changed)
        self.primary_use_input_audio.trace_add("write", self.on_primary_audio_source_changed)
        self.secondary_audio_mode.trace_add("write", self.on_secondary_audio_mode_changed)

    # ------------------------------------------------------------------ state

    def load_language_packs(self):
        packs = default_language_packs()

        if self.lang_dir.exists():
            for path in sorted(self.lang_dir.glob("*.json")):
                try:
                    with open(path, "r", encoding="utf-8") as file:
                        data = json.load(file)
                except Exception:
                    continue

                code = str(data.get("language_code") or path.stem).strip() or path.stem
                name = str(data.get("language_name") or code).strip() or code
                translations = data.get("translations", {})
                if not isinstance(translations, dict):
                    continue

                packs[code] = {
                    "language_code": code,
                    "language_name": name,
                    "translations": {str(k): str(v) for k, v in translations.items()},
                }

        return packs

    def language_display_names(self):
        names = {}

        # Public build default order:
        # Japanese first, English second, then the rest.
        ordered_codes = []

        for preferred in ("ja", "en"):
            if preferred in self.language_packs:
                ordered_codes.append(preferred)

        for code in self.language_packs:
            if code not in ordered_codes:
                ordered_codes.append(code)

        for code in ordered_codes:
            data = self.language_packs.get(code, {})
            name = data.get("language_name") or code
            names[name] = code

        return names

    def default_language_name(self):
        # Default UI language for public builds.
        if "ja" in self.language_packs:
            return self.language_packs["ja"].get("language_name", "Japanese")
        if "en" in self.language_packs:
            return self.language_packs["en"].get("language_name", "English")
        return next(iter(self.language_names.keys()), "Japanese")

    def current_language_code(self):
        name = self.ui_language.get() if getattr(self, "ui_language", None) is not None else "English"
        return self.language_names.get(name, "en")

    def t(self, text):
        code = self.current_language_code()
        pack = self.language_packs.get(code, {})
        translations = pack.get("translations", {})
        return translations.get(text, text)

    def on_ui_language_changed(self, *_):
        if hasattr(self, "root_frame"):
            self.after_idle(self.build_ui)

    def on_video_size_changed(self, *_):
        if self.video_size.get() == "720x480":
            self.video_bitrate.set("6400k")
            self.video_maxrate.set("7000k")
            self.video_bufsize.set("3200k")
            return

        if self.video_bitrate.get().strip().lower() in ("6400k", "6.4m", "6.4mbps"):
            self.video_bitrate.set("13M")
        if self.video_maxrate.get().strip().lower() in ("7000k", "7m", "7mbps"):
            self.video_maxrate.set("14M")
        if self.video_bufsize.get().strip().lower() in ("3200k", "3.2m", "3.2mbps"):
            self.video_bufsize.set("8M")

    def on_audio_mode_changed(self, *_):
        self.audio_bitrate.set({"Mono": "96k", "Surround": "320k"}.get(self.audio_mode.get(), "256k"))
        self.update_secondary_audio_state()

    def on_secondary_audio_mode_changed(self, *_):
        self.secondary_audio_bitrate.set("96k" if self.secondary_audio_mode.get() == "Mono" else "256k")

    def update_secondary_audio_state(self, *_):
        locked = self.audio_mode.get() == "Surround"
        for widget, normal_state in self.secondary_audio_controls:
            try:
                widget.configure(state="disabled" if locked else normal_state)
            except tk.TclError:
                pass

    def on_primary_audio_source_changed(self, *_):
        if not hasattr(self, "primary_audio_entry"):
            return
        state = "disabled" if self.primary_use_input_audio.get() == "on" else "normal"
        self.primary_audio_entry.configure(state=state)
        self.primary_audio_browse.configure(state=state)

    # ------------------------------------------------------------------ UI

    def build_ui(self):
        self.configure_style()

        old_root = getattr(self, "root_frame", None)
        if old_root is not None:
            old_root.destroy()

        root = ttk.Frame(self, padding=8)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)
        self.root_frame = root

        io_area = ttk.Frame(root)
        io_area.grid(row=0, column=0, sticky="ew")

        files_area = ttk.Frame(root)
        files_area.grid(row=1, column=0, sticky="ew")

        tabs_area = ttk.Frame(root)
        tabs_area.grid(row=2, column=0, sticky="nsew")
        tabs_area.columnconfigure(0, weight=1)
        tabs_area.rowconfigure(0, weight=1)

        bottom_area = ttk.Frame(root)
        bottom_area.grid(row=3, column=0, sticky="ew")

        self.build_io_section(io_area)
        self.build_file_section(files_area)
        self.build_tabs(tabs_area)
        self.build_bottom_bar(bottom_area)

    def configure_style(self):
        try:
            ttk.Style().theme_use("classic")
        except tk.TclError:
            pass

        style = ttk.Style()
        style.configure(
            "TCombobox",
            fieldbackground="white",
            background="white",
            foreground="black",
            selectbackground="white",
            selectforeground="black",
            arrowcolor="black",
        )
        style.map(
            "TCombobox",
            fieldbackground=[("disabled", "#e0e0e0"), ("readonly", "white"), ("!disabled", "white")],
            background=[("disabled", "#e0e0e0"), ("readonly", "white"), ("!disabled", "white")],
            foreground=[("disabled", "#777777"), ("readonly", "black"), ("!disabled", "black")],
            selectbackground=[("disabled", "#e0e0e0"), ("readonly", "white"), ("!disabled", "white")],
            selectforeground=[("disabled", "#777777"), ("readonly", "black"), ("!disabled", "black")],
            arrowcolor=[("disabled", "#777777"), ("!disabled", "black")],
        )

        try:
            style.layout(
                "TNotebook.Tab",
                [
                    (
                        "Notebook.tab",
                        {
                            "sticky": "nswe",
                            "children": [
                                (
                                    "Notebook.padding",
                                    {
                                        "side": "top",
                                        "sticky": "nswe",
                                        "children": [("Notebook.label", {"side": "top", "sticky": ""})],
                                    },
                                )
                            ],
                        },
                    )
                ],
            )
        except tk.TclError:
            pass

        self.option_add("*Listbox.background", "white")
        self.option_add("*Listbox.foreground", "black")
        self.option_add("*TCombobox*Listbox.background", "white")
        self.option_add("*TCombobox*Listbox.foreground", "black")

    def build_io_section(self, parent):
        frame = ttk.LabelFrame(parent, text=self.t("Input / Output"))
        frame.pack(fill="x", pady=(0, 8))
        self.language_select_row(frame)
        self.path_row(frame, "ffmpeg", self.ffmpeg_path, self.select_ffmpeg)
        self.path_row(frame, "Save as", self.output_path, self.select_output_file)

    def build_file_section(self, parent):
        frame = ttk.LabelFrame(parent, text=self.t("Files"))
        frame.pack(fill="x", pady=(0, 8))

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Button(buttons, text=self.t("Add"), width=10, command=self.add_files).pack(side="left")
        ttk.Button(buttons, text=self.t("Clear"), width=10, command=self.clear_files).pack(side="left", padx=(6, 0))

        self.file_list = tk.Listbox(
            frame,
            height=5,
            bg="white",
            fg="black",
            selectbackground="#0078D7",
            selectforeground="white",
        )
        self.file_list.pack(fill="x", padx=8, pady=(0, 8))
        for path in self.input_files:
            self.file_list.insert("end", path)

    def build_tabs(self, parent):
        self.tabs = ttk.Notebook(parent)
        self.tabs.pack(fill="both", expand=True, pady=(0, 8))

        tabs = {
            "Video": "video_tab",
            "Audio": "audio_tab",
            "TS Info": "ts_info_tab",
            "Program": "program_tab",
            "Log": "log_tab",
        }
        for label, attr in tabs.items():
            frame = ttk.Frame(self.tabs, padding=8)
            setattr(self, attr, frame)
            self.tabs.add(frame, text=self.t(label))

        self.build_video_tab()
        self.build_audio_tab()
        self.build_ts_info_tab()
        self.build_program_tab()
        self.build_log_tab()

    def build_bottom_bar(self, parent):
        bottom = ttk.Frame(parent)
        bottom.pack(fill="x")

        self.start_button = ttk.Button(bottom, text=self.t("Encode"), width=14, command=self.start_encode)
        self.start_button.pack(side="left")

        self.stop_button = ttk.Button(bottom, text=self.t("Stop"), width=14, command=self.stop_encode, state="disabled")
        self.stop_button.pack(side="left", padx=(6, 0))

        self.status = tk.StringVar(value=self.t("Ready"))
        ttk.Label(bottom, textvariable=self.status, relief="sunken", anchor="w").pack(
            side="left",
            fill="x",
            expand=True,
            padx=(8, 0),
        )

    def system_background(self):
        try:
            bg = ttk.Style().lookup("TFrame", "background")
            if bg:
                return bg
        except tk.TclError:
            pass
        return self.cget("background")

    def is_list_scroll_target(self, widget):
        try:
            widget_class = widget.winfo_class()
            widget_path = str(widget)
        except tk.TclError:
            return False

        # When a ttk.Combobox dropdown is open, its popup list is a Tk Listbox
        # outside the tab canvas. Do not let the tab-level mouse-wheel binding
        # steal wheel events from that list.
        if widget_class in {"Listbox", "TCombobox", "Combobox"}:
            return True

        # Tk/ttk combobox popup widgets often contain "popdown" in their path.
        if "popdown" in widget_path.lower():
            return True

        return False

    def make_scroll_frame(self, parent):
        bg = self.system_background()

        # Keep the scrollable canvas and the inner content frame on the same
        # system background. Otherwise the unused scroll area can appear white.
        canvas = tk.Canvas(
            parent,
            highlightthickness=0,
            borderwidth=0,
            background=bg,
            selectbackground=bg,
        )
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.pack(side="left", fill="both", expand=True)

        main = tk.Frame(canvas, bg=bg, highlightthickness=0, borderwidth=0)
        window_id = canvas.create_window((0, 0), window=main, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scroll_state = {"needed": False, "visible": False}

        def set_scrollbar_visible(visible):
            if visible == scroll_state["visible"]:
                return
            scroll_state["visible"] = visible
            if visible:
                scrollbar.pack(side="right", fill="y")
            else:
                scrollbar.pack_forget()
                canvas.yview_moveto(0)

        def update_scrollregion(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

            content_height = max(main.winfo_reqheight(), main.winfo_height())
            canvas_height = canvas.winfo_height()
            needed = content_height > canvas_height + 2
            scroll_state["needed"] = needed
            set_scrollbar_visible(needed)

        def resize_inner(event):
            # Keep the inner frame exactly as wide as the visible canvas.
            # If the tab is wide enough, this prevents horizontal drifting.
            canvas.itemconfigure(window_id, width=event.width)
            update_scrollregion()

        def on_mousewheel(event):
            if self.is_list_scroll_target(event.widget):
                return None

            if not scroll_state["needed"]:
                return "break"

            canvas.yview_scroll(int(-event.delta / 120), "units")
            return "break"

        main.bind("<Configure>", update_scrollregion)
        canvas.bind("<Configure>", resize_inner)
        canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))

        return main

    def bind_input_context_menu(self, widget):
        widget.bind("<Button-3>", lambda event, w=widget: self.show_input_context_menu(event, w))
        widget.bind("<Control-Button-1>", lambda event, w=widget: self.show_input_context_menu(event, w))
        return widget

    def show_input_context_menu(self, event, widget):
        widget.focus_set()
        menu = tk.Menu(self, tearoff=0)
        for label, action in (
            (self.t("Cut"), "<<Cut>>"),
            (self.t("Copy"), "<<Copy>>"),
            (self.t("Paste"), "<<Paste>>"),
        ):
            menu.add_command(label=label, command=lambda a=action: self.input_menu_event(widget, a))
        menu.add_separator()
        menu.add_command(label=self.t("Select All"), command=lambda: self.select_all_in_widget(widget))

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    @staticmethod
    def input_menu_event(widget, virtual_event):
        try:
            widget.event_generate(virtual_event)
        except tk.TclError:
            pass

    @staticmethod
    def select_all_in_widget(widget):
        try:
            if isinstance(widget, tk.Text):
                widget.tag_add("sel", "1.0", "end-1c")
                widget.mark_set("insert", "1.0")
            else:
                widget.selection_range(0, "end")
                widget.icursor("end")
        except tk.TclError:
            pass

    def path_row(self, parent, label, variable, command):
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=8, pady=(8, 0))
        ttk.Label(row, text=self.t(label), width=18).pack(side="left")

        entry = ttk.Entry(row, textvariable=variable)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.bind_input_context_menu(entry)

        ttk.Button(row, text=self.t("Browse"), width=10, command=command).pack(side="left")
        return entry

    def language_select_row(self, parent):
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=8, pady=(8, 0))
        ttk.Label(row, text=self.t("UI Language"), width=18).pack(side="left")

        combo = ttk.Combobox(
            row,
            textvariable=self.ui_language,
            values=list(self.language_names.keys()),
            state="readonly",
            width=20,
        )
        combo.pack(side="left", fill="x", expand=False)
        self.bind_input_context_menu(combo)
        return combo

    def combo_row(self, parent, row, label, variable, values):
        ttk.Label(parent, text=self.t(label), width=18).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)

        combo = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", width=24)
        combo.grid(row=row, column=1, sticky="w", pady=4)
        self.bind_input_context_menu(combo)
        return combo

    def entry_row(self, parent, row, label, variable, width=36):
        ttk.Label(parent, text=self.t(label), width=18).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)

        entry = ttk.Entry(parent, textvariable=variable, width=width)
        entry.grid(row=row, column=1, sticky="w", pady=4)
        self.bind_input_context_menu(entry)
        return entry

    def xml_button_row(self, parent, row, import_text, import_command, export_text, export_command):
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=1, sticky="w", pady=(4, 8))
        ttk.Button(frame, text=self.t(import_text), width=12, command=import_command).pack(side="left")
        ttk.Button(frame, text=self.t(export_text), width=12, command=export_command).pack(side="left", padx=(6, 0))
        return frame

    def text_row(self, parent, row, label, initial_text="", height=4):
        ttk.Label(parent, text=self.t(label), width=18).grid(row=row, column=0, sticky="nw", padx=(0, 8), pady=4)

        text = tk.Text(parent, width=58, height=height, wrap="word", bg="white", fg="black", insertbackground="black")
        text.grid(row=row, column=1, sticky="we", pady=4)
        text.insert("1.0", initial_text)
        self.bind_input_context_menu(text)
        return text

    def build_video_tab(self):
        main = self.make_scroll_frame(self.video_tab)

        frame = ttk.LabelFrame(main, text=self.t("Video"))
        frame.pack(fill="x", anchor="n", padx=(0, 8), pady=(0, 8))
        grid = ttk.Frame(frame)
        grid.pack(fill="x", padx=8, pady=8)

        self.combo_row(grid, 0, "Size", self.video_size, ["1920x1080", "1440x1080", "1280x720", "720x480"])
        self.combo_row(grid, 1, "Scan", self.scan_mode, ["60i", "60p"])
        self.combo_row(grid, 2, "Aspect", self.output_aspect, ["16:9", "4:3"])
        self.entry_row(grid, 3, "Bitrate", self.video_bitrate)
        self.entry_row(grid, 4, "Maxrate", self.video_maxrate)
        self.entry_row(grid, 5, "Bufsize", self.video_bufsize)
        self.entry_row(grid, 6, "GOP", self.gop)

    def build_audio_tab(self):
        main = self.make_scroll_frame(self.audio_tab)
        bg = self.cget("background")

        primary = ttk.LabelFrame(main, text=self.t("Primary Audio"))
        primary.pack(fill="x", anchor="n", pady=(0, 8))
        grid = ttk.Frame(primary)
        grid.pack(fill="x", padx=8, pady=8)

        tk.Checkbutton(
            grid,
            text=self.t("Use input audio"),
            variable=self.primary_use_input_audio,
            onvalue="on",
            offvalue="off",
            bg=bg,
            activebackground=bg,
            highlightthickness=0,
            bd=0,
        ).grid(row=0, column=1, sticky="w", pady=(0, 8))

        ttk.Label(grid, text=self.t("Audio file"), width=18).grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.primary_audio_entry = ttk.Entry(grid, textvariable=self.primary_audio_path, width=52)
        self.primary_audio_entry.grid(row=1, column=1, sticky="we", pady=4)
        self.bind_input_context_menu(self.primary_audio_entry)
        self.primary_audio_browse = ttk.Button(grid, text=self.t("Browse"), width=10, command=self.select_primary_audio)
        self.primary_audio_browse.grid(row=1, column=2, sticky="w", padx=(6, 0), pady=4)

        self.combo_row(grid, 2, "Mode", self.audio_mode, ["Stereo", "Mono", "Surround"])
        self.combo_row(grid, 3, "Bitrate", self.audio_bitrate, AUDIO_BITRATES)
        self.combo_row(grid, 4, "Sample rate", self.audio_samplerate, ["48000", "44100"])
        self.combo_row(grid, 5, "Language", self.primary_audio_language, LANGUAGE_OPTIONS)
        self.entry_row(grid, 6, "Track name", self.primary_audio_title)
        grid.columnconfigure(1, weight=1)

        secondary = ttk.LabelFrame(main, text=self.t("Secondary Audio"))
        secondary.pack(fill="x", anchor="n")
        sec_grid = ttk.Frame(secondary)
        sec_grid.pack(fill="x", padx=8, pady=8)

        ttk.Label(sec_grid, text=self.t("Audio file"), width=18).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        secondary_entry = ttk.Entry(sec_grid, textvariable=self.secondary_audio_path, width=52)
        secondary_entry.grid(row=0, column=1, sticky="we", pady=4)
        self.bind_input_context_menu(secondary_entry)

        browse = ttk.Button(sec_grid, text=self.t("Browse"), width=10, command=self.select_secondary_audio)
        browse.grid(row=0, column=2, sticky="w", padx=(6, 0), pady=4)

        controls = [
            (secondary_entry, "normal"),
            (browse, "normal"),
            (self.combo_row(sec_grid, 1, "Mode", self.secondary_audio_mode, ["Stereo", "Mono"]), "readonly"),
            (self.combo_row(sec_grid, 2, "Bitrate", self.secondary_audio_bitrate, AUDIO_BITRATES), "readonly"),
            (self.combo_row(sec_grid, 3, "Sample rate", self.secondary_audio_samplerate, ["48000", "44100"]), "readonly"),
            (self.combo_row(sec_grid, 4, "Language", self.secondary_audio_language, LANGUAGE_OPTIONS), "readonly"),
            (self.entry_row(sec_grid, 5, "Track name", self.secondary_audio_title), "normal"),
        ]
        self.secondary_audio_controls.extend(controls)
        sec_grid.columnconfigure(1, weight=1)

        self.on_primary_audio_source_changed()
        self.update_secondary_audio_state()

    def build_ts_info_tab(self):
        main = self.make_scroll_frame(self.ts_info_tab)
        bg = self.cget("background")

        ts_frame = ttk.LabelFrame(main, text=self.t("NIT / Station Profile"))
        ts_frame.pack(fill="x", anchor="n", padx=(0, 8), pady=(0, 8))
        grid = ttk.Frame(ts_frame)
        grid.pack(fill="x", padx=8, pady=8)

        tk.Checkbutton(
            grid,
            text=self.t("Inject TS information with TSDuck"),
            variable=self.ts_info_enabled,
            onvalue="on",
            offvalue="off",
            bg=bg,
            activebackground=bg,
            highlightthickness=0,
            bd=0,
        ).grid(row=0, column=1, sticky="w", pady=(0, 8))

        ttk.Label(grid, text=self.t("tsp.exe"), width=18).grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        tsduck_entry = ttk.Entry(grid, textvariable=self.tsduck_path, width=52)
        tsduck_entry.grid(row=1, column=1, sticky="we", pady=4)
        self.bind_input_context_menu(tsduck_entry)
        ttk.Button(grid, text=self.t("Browse"), width=10, command=self.select_tsduck).grid(row=1, column=2, sticky="w", padx=(6, 0), pady=4)

        self.xml_button_row(grid, 2, "Import", self.import_nit_xml_file, "Export", self.export_nit_xml_file)

        ts_rows = [
            ("Network Name", self.network_name),
            ("TS Name", self.ts_name),
            ("Provider", self.provider_name),
            ("Service Base", self.service_name),
            ("Service ID", self.service_id),
            ("OneSeg Service ID", self.oneseg_service_id),
            ("TS ID", self.transport_stream_id),
            ("Original NW ID", self.original_network_id),
            ("Network ID", self.network_id),
            ("Remote Key ID", self.remote_control_key_id),
            ("Service Type", self.service_type),
        ]
        for index, (label, variable) in enumerate(ts_rows, start=3):
            self.entry_row(grid, index, label, variable)
        grid.columnconfigure(1, weight=1)

        self.build_physical_channels_section(main)
        self.build_service_names_section(main)
        self.build_cat_section(main, bg)

    def build_cat_section(self, parent, bg):
        frame = ttk.LabelFrame(parent, text=self.t("CAT / Access Control"))
        frame.pack(fill="x", anchor="n", padx=(0, 8), pady=(0, 8))
        grid = ttk.Frame(frame)
        grid.pack(fill="x", padx=8, pady=8)

        tk.Checkbutton(
            grid,
            text=self.t("Inject CAT"),
            variable=self.cat_enabled,
            onvalue="on",
            offvalue="off",
            bg=bg,
            activebackground=bg,
            highlightthickness=0,
            bd=0,
        ).grid(row=0, column=1, sticky="w", pady=(0, 8))

        self.xml_button_row(grid, 1, "Import", self.import_cat_xml_file, "Export", self.export_cat_xml_file)

        for index, (label, variable) in enumerate(
            [
                ("CAT Version", self.cat_version),
                ("CA System ID", self.cat_ca_system_id),
                ("Transmission Type", self.cat_transmission_type),
                ("EMM PID", self.cat_pid),
                ("Private Data", self.cat_private_data),
            ],
            start=2,
        ):
            self.entry_row(grid, index, label, variable)

    def build_service_names_section(self, parent):
        frame = ttk.LabelFrame(parent, text=self.t("SDT / Service Names"))
        frame.pack(fill="x", anchor="n", padx=(0, 8), pady=(0, 8))
        grid = ttk.Frame(frame)
        grid.pack(fill="x", padx=8, pady=8)

        self.xml_button_row(grid, 0, "Import", self.import_sdt_xml_file, "Export", self.export_sdt_xml_file)

        for index, (label, variable) in enumerate(
            [
                ("Service 1", self.service_name_1),
                ("Service 2", self.service_name_2),
                ("Service 3", self.service_name_3),
                ("OneSeg", self.service_name_1seg),
            ],
            start=1,
        ):
            self.entry_row(grid, index, label, variable)

    def build_physical_channels_section(self, parent):
        frame = ttk.LabelFrame(parent, text=self.t("Physical Channels"))
        frame.pack(fill="x", anchor="n", padx=(0, 8), pady=(0, 8))
        grid = ttk.Frame(frame)
        grid.pack(fill="x", padx=8, pady=8)

        for index, variable in enumerate(self.physical_channels):
            row = index // 2
            col = (index % 2) * 2
            ttk.Label(grid, text=f"{self.t('Relay Station')}{index + 1}", width=10).grid(row=row, column=col, sticky="w", padx=(0, 8), pady=4)
            entry = ttk.Entry(grid, textvariable=variable, width=12)
            entry.grid(row=row, column=col + 1, sticky="w", padx=(0, 18), pady=4)
            self.bind_input_context_menu(entry)

    def build_program_tab(self):
        main = self.make_scroll_frame(self.program_tab)
        bg = self.cget("background")

        eit_frame = ttk.LabelFrame(main, text=self.t("EIT Present Event"))
        eit_frame.pack(fill="x", anchor="n", pady=(0, 8))
        grid = ttk.Frame(eit_frame)
        grid.pack(fill="x", padx=8, pady=8)

        tk.Checkbutton(
            grid,
            text=self.t("Inject EIT"),
            variable=self.eit_enabled,
            onvalue="on",
            offvalue="off",
            bg=bg,
            activebackground=bg,
            highlightthickness=0,
            bd=0,
        ).grid(row=0, column=1, sticky="w", pady=(0, 8))

        self.entry_row(grid, 1, "Event ID", self.event_id)
        self.entry_row(grid, 2, "Event Name", self.event_name)
        self.description_text = self.text_row(grid, 3, "Description", self.event_text.get(), height=4)
        self.entry_row(grid, 4, "Start Time", self.event_start_time)
        self.entry_row(grid, 5, "Duration", self.event_duration)
        self.combo_row(grid, 6, "Language", self.event_language, LANGUAGE_OPTIONS)
        self.combo_row(grid, 7, "Running Status", self.event_running_status, ["running", "not-running", "pausing", "undefined"])
        self.combo_row(grid, 8, "Genre", self.genre, GENRE_OPTIONS)
        grid.columnconfigure(1, weight=1)

        tot_frame = ttk.LabelFrame(main, text=self.t("TOT"))
        tot_frame.pack(fill="x", anchor="n")
        tot_grid = ttk.Frame(tot_frame)
        tot_grid.pack(fill="x", padx=8, pady=8)

        tk.Checkbutton(
            tot_grid,
            text=self.t("Inject TOT"),
            variable=self.tot_enabled,
            onvalue="on",
            offvalue="off",
            bg=bg,
            activebackground=bg,
            highlightthickness=0,
            bd=0,
        ).grid(row=0, column=1, sticky="w", pady=(0, 8))

        self.combo_row(tot_grid, 1, "Time Source", self.tot_time_source, ["manual", "system"])
        self.entry_row(tot_grid, 2, "Manual Time", self.tot_start_time)

    def build_log_tab(self):
        self.log = ScrolledText(self.log_tab, height=15, wrap="none", bg="white", fg="black", insertbackground="black")
        self.log.pack(fill="both", expand=True)
        self.bind_input_context_menu(self.log)

        buttons = ttk.Frame(self.log_tab)
        buttons.pack(fill="x", pady=(6, 0))
        ttk.Button(buttons, text=self.t("Clear"), width=10, command=self.clear_log).pack(side="left")

    # ------------------------------------------------------------------ file dialogs

    def ask_file(self, title, filetypes):
        initial_dir = default_exe_dir() if default_exe_dir().exists() else app_base_dir()
        return filedialog.askopenfilename(title=title, filetypes=filetypes, initialdir=str(initial_dir))

    def select_ffmpeg(self):
        path = self.ask_file(self.t("Select ffmpeg.exe"), [("ffmpeg.exe", "ffmpeg.exe"), ("Executable", "*.exe"), (self.t("All files"), "*.*")])
        if path:
            self.ffmpeg_path.set(path)

    def select_tsduck(self):
        path = self.ask_file(self.t("Select tsp.exe"), [("tsp.exe", "tsp.exe"), ("Executable", "*.exe"), (self.t("All files"), "*.*")])
        if path:
            self.tsduck_path.set(path)

    def import_sdt_xml_file(self):
        self.import_single_xml_section("SDT", self.import_sdt_xml)

    def import_nit_xml_file(self):
        self.import_single_xml_section("NIT", self.import_nit_xml)

    def import_cat_xml_file(self):
        self.import_single_xml_section("CAT", self.import_cat_xml)

    def export_sdt_xml_file(self):
        self.export_single_xml_section("SDT")

    def export_nit_xml_file(self):
        self.export_single_xml_section("NIT")

    def export_cat_xml_file(self):
        self.export_single_xml_section("CAT")

    def import_single_xml_section(self, section_name, import_func):
        path = filedialog.askopenfilename(
            title=f"Import {section_name} XML",
            filetypes=[("TSDuck XML", "*.xml"), (self.t("All files"), "*.*")],
        )
        if not path:
            return

        try:
            root = ET.parse(path).getroot()
            if self.first_xml_element(root, section_name) is None:
                messagebox.showwarning("Import XML", f"No {section_name} section was found.")
                return

            import_func(root)
            self.ts_info_enabled.set("on")
            messagebox.showinfo("Import XML", f"Imported {section_name}: {path}")
        except Exception as exc:
            messagebox.showerror("Import XML", str(exc))

    def export_single_xml_section(self, section_name):
        default_name = f"makets_{section_name.lower()}.xml"
        path = filedialog.asksaveasfilename(
            title=f"Export {section_name} XML",
            defaultextension=".xml",
            initialfile=default_name,
            filetypes=[("TSDuck XML", "*.xml"), (self.t("All files"), "*.*")],
        )
        if not path:
            return

        try:
            source = self.make_xml_section_temp_file(section_name)
            shutil.copyfile(source, path)
            messagebox.showinfo("Export XML", f"Exported {section_name}:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export XML", str(exc))

    def make_xml_section_temp_file(self, section_name):
        base = "makets_export"
        if section_name in ("SDT", "NIT"):
            sdt_path, nit_path = self.write_tsduck_xml_files(base)
            return sdt_path if section_name == "SDT" else nit_path

        if section_name == "CAT":
            return self.write_cat_xml_file(base)

        raise ValueError(f"Unsupported section: {section_name}")

    def import_tsduck_xml(self):
        paths = filedialog.askopenfilenames(
            title="Import TSDuck XML",
            filetypes=[("TSDuck XML", "*.xml"), (self.t("All files"), "*.*")],
        )
        if not paths:
            return

        imported = []
        errors = []

        for path in paths:
            try:
                root = ET.parse(path).getroot()
                found = self.import_tsduck_xml_root(root)
                if found:
                    imported.extend(found)
            except Exception as exc:
                errors.append(f"{os.path.basename(path)}: {exc}")

        if imported:
            self.ts_info_enabled.set("on")
            messagebox.showinfo("Import XML", "Imported: " + ", ".join(sorted(set(imported))))

        if errors:
            messagebox.showwarning("Import XML", "\n".join(errors))

        if not imported and not errors:
            messagebox.showwarning("Import XML", "No SDT, NIT, or CAT section was found.")

    def export_tsduck_xml(self):
        folder = filedialog.askdirectory(title="Export TSDuck XML")
        if not folder:
            return

        try:
            base = "makets_tsinfo"
            temp_sdt, temp_nit = self.write_tsduck_xml_files(base)
            exported = []

            targets = [
                (temp_sdt, os.path.join(folder, "makets_sdt.xml")),
                (temp_nit, os.path.join(folder, "makets_nit.xml")),
            ]

            if self.is_cat_enabled():
                temp_cat = self.write_cat_xml_file(base)
                targets.append((temp_cat, os.path.join(folder, "makets_cat.xml")))

            for source, target in targets:
                shutil.copyfile(source, target)
                exported.append(target)

            messagebox.showinfo("Export XML", "Exported:\n" + "\n".join(exported))
        except Exception as exc:
            messagebox.showerror("Export XML", str(exc))

    def import_tsduck_xml_root(self, root):
        found = []

        if self.first_xml_element(root, "SDT") is not None:
            self.import_sdt_xml(root)
            found.append("SDT")

        if self.first_xml_element(root, "NIT") is not None:
            self.import_nit_xml(root)
            found.append("NIT")

        if self.first_xml_element(root, "CAT") is not None:
            self.import_cat_xml(root)
            found.append("CAT")

        return found

    @staticmethod
    def xml_local_name(element):
        return element.tag.rsplit("}", 1)[-1]

    def xml_elements(self, root, tag):
        return [element for element in root.iter() if self.xml_local_name(element) == tag]

    def first_xml_element(self, root, tag):
        for element in root.iter():
            if self.xml_local_name(element) == tag:
                return element
        return None

    @staticmethod
    def set_if_present(variable, value):
        if value is not None and str(value) != "":
            variable.set(str(value))

    @staticmethod
    def xml_text(element):
        if element is None:
            return ""
        return "".join(element.itertext()).strip()

    def import_sdt_xml(self, root):
        sdt = self.first_xml_element(root, "SDT")
        if sdt is None:
            return

        self.set_if_present(self.transport_stream_id, sdt.get("transport_stream_id"))
        self.set_if_present(self.original_network_id, sdt.get("original_network_id"))

        full_services = []
        oneseg_service = None
        provider = None
        first_service_type = None

        for service in self.xml_elements(sdt, "service"):
            service_id = service.get("service_id")
            descriptor = self.first_xml_element(service, "service_descriptor")
            if descriptor is None:
                continue

            service_type = descriptor.get("service_type", "")
            service_name = descriptor.get("service_name", "")
            provider_name = descriptor.get("service_provider_name", "")

            if provider is None and provider_name:
                provider = provider_name
            if first_service_type is None and service_type:
                first_service_type = service_type

            if service_type.lower() == "0xc0":
                oneseg_service = (service_id, service_name)
            else:
                full_services.append((service_id, service_name, service_type))

        if full_services:
            self.set_if_present(self.service_id, full_services[0][0])
            self.set_if_present(self.service_name_1, full_services[0][1])
            self.set_if_present(self.service_type, full_services[0][2])
        if len(full_services) > 1:
            self.set_if_present(self.service_name_2, full_services[1][1])
        if len(full_services) > 2:
            self.set_if_present(self.service_name_3, full_services[2][1])

        if oneseg_service:
            self.set_if_present(self.oneseg_service_id, oneseg_service[0])
            self.set_if_present(self.service_name_1seg, oneseg_service[1])

        self.set_if_present(self.provider_name, provider or "")
        if full_services:
            base = re.sub(r"[・･\s]*[１２３123]$", "", full_services[0][1]).strip()
            if base:
                self.service_name.set(base)

    def import_nit_xml(self, root):
        nit = self.first_xml_element(root, "NIT")
        if nit is None:
            return

        self.set_if_present(self.network_id, nit.get("network_id"))

        network_name = self.first_xml_element(nit, "network_name_descriptor")
        if network_name is not None:
            self.set_if_present(self.network_name, network_name.get("network_name"))

        transport_stream = self.first_xml_element(nit, "transport_stream")
        if transport_stream is not None:
            self.set_if_present(self.transport_stream_id, transport_stream.get("transport_stream_id"))
            self.set_if_present(self.original_network_id, transport_stream.get("original_network_id"))

        ts_info = self.first_xml_element(nit, "TS_information_descriptor")
        if ts_info is not None:
            self.set_if_present(self.remote_control_key_id, ts_info.get("remote_control_key_id"))
            self.set_if_present(self.ts_name, ts_info.get("ts_name"))
            self.set_if_present(self.service_name, ts_info.get("ts_name"))

        self.import_nit_service_list(nit)
        self.import_nit_physical_channels(nit)

    def import_nit_service_list(self, nit):
        full_service_ids = []
        oneseg_id = None

        for service in self.xml_elements(nit, "service"):
            service_id = service.get("service_id") or service.get("id")
            service_type = (service.get("service_type") or "").lower()

            if not service_id:
                continue
            if service_type == "0xc0":
                oneseg_id = service_id
            elif service_type == "0x01":
                full_service_ids.append(service_id)

        if full_service_ids:
            self.service_id.set(full_service_ids[0])
        if oneseg_id:
            self.oneseg_service_id.set(oneseg_id)

    def import_nit_physical_channels(self, nit):
        channels = []
        for frequency in self.xml_elements(nit, "frequency"):
            channel = self.frequency_value_to_physical_channel(frequency.get("value", ""))
            if channel is not None and channel not in channels:
                channels.append(channel)

        for index, variable in enumerate(self.physical_channels):
            variable.set(str(channels[index]) if index < len(channels) else "")

    def frequency_value_to_physical_channel(self, value):
        digits = re.sub(r"[^0-9]", "", str(value))
        if not digits:
            return None

        frequency_hz = int(digits)
        channel = round((frequency_hz - 473_142_857) / 6_000_000) + 13

        if channel < 13 or channel > 62:
            return None

        expected = self.physical_channel_to_frequency_hz(str(channel))
        if expected is None or abs(expected - frequency_hz) > 250_000:
            return None

        return channel

    def import_cat_xml(self, root):
        cat = self.first_xml_element(root, "CAT")
        if cat is None:
            return

        self.cat_enabled.set("on")
        self.set_if_present(self.cat_version, cat.get("version"))

        descriptor = self.first_xml_element(cat, "ISDB_access_control_descriptor")
        if descriptor is None:
            return

        self.set_if_present(self.cat_ca_system_id, descriptor.get("CA_system_id"))
        self.set_if_present(self.cat_transmission_type, descriptor.get("transmission_type"))
        self.set_if_present(self.cat_pid, descriptor.get("PID"))

        private_data = self.first_xml_element(descriptor, "private_data")
        private_text = re.sub(r"\s+", " ", self.xml_text(private_data)).strip()
        if private_text:
            self.cat_private_data.set(private_text)

    def select_primary_audio(self):
        path = self.ask_file(
            self.t("Select primary audio file"),
            [(self.t("Audio files"), AUDIO_FILE_PATTERN), (self.t("All files"), "*.*")],
        )
        if path:
            self.primary_audio_path.set(path)

    def select_secondary_audio(self):
        path = self.ask_file(
            self.t("Select secondary audio file"),
            [(self.t("Audio files"), AUDIO_FILE_PATTERN), (self.t("All files"), "*.*")],
        )
        if path:
            self.secondary_audio_path.set(path)

    def select_output_file(self):
        path = filedialog.asksaveasfilename(
            title=self.t("Save as"),
            defaultextension=".ts",
            filetypes=[(self.t("MPEG2-TS files"), "*.ts"), (self.t("All files"), "*.*")],
        )
        if path:
            self.output_path.set(path)

    def add_files(self):
        paths = filedialog.askopenfilenames(
            title=self.t("Select files"),
            filetypes=[
                (self.t("Video files"), "*.mp4 *.mov *.mkv *.avi *.m2ts *.ts *.mpg *.mpeg *.wmv *.flv *.webm"),
                (self.t("All files"), "*.*"),
            ],
        )
        for path in paths:
            if path not in self.input_files:
                self.input_files.append(path)
                self.file_list.insert("end", path)

    def clear_files(self):
        self.input_files.clear()
        self.file_list.delete(0, "end")

    def clear_log(self):
        self.log.delete("1.0", "end")

    # ------------------------------------------------------------------ probe / color

    def get_ffprobe_path(self):
        ffmpeg = self.ffmpeg_path.get().strip()
        default_ffprobe = default_exe_dir() / exe_name("ffprobe")

        if not ffmpeg or ffmpeg == "ffmpeg":
            return str(default_ffprobe) if default_ffprobe.exists() else "ffprobe"

        folder = os.path.dirname(ffmpeg)
        name = os.path.basename(ffmpeg).lower()
        if name == "ffmpeg.exe":
            return os.path.join(folder, "ffprobe.exe")
        if name == "ffmpeg":
            return os.path.join(folder, "ffprobe")
        return str(default_ffprobe) if default_ffprobe.exists() else "ffprobe"

    def probe_video_info(self, input_path):
        info = self.probe_video_info_by_ffprobe(input_path)
        if not info or self.is_color_info_missing(info):
            fallback = self.probe_video_info_by_ffmpeg_banner(input_path)
            info = {**info, **{k: v for k, v in fallback.items() if not info.get(k)}} if fallback else info
        return info

    @staticmethod
    def is_color_info_missing(info):
        return not all(info.get(key) for key in ("width", "height", "color_space", "color_primaries", "color_transfer"))

    def run_probe(self, cmd):
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            return result
        except Exception:
            return None

    def probe_video_info_by_ffprobe(self, input_path):
        cmd = [
            self.get_ffprobe_path(),
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,avg_frame_rate,r_frame_rate,color_space,color_primaries,color_transfer,color_range",
            "-of",
            "json",
            input_path,
        ]
        result = self.run_probe(cmd)
        if not result or result.returncode != 0:
            return {}

        try:
            streams = json.loads(result.stdout).get("streams", [])
            return streams[0] if streams else {}
        except json.JSONDecodeError:
            return {}

    def probe_video_info_by_ffmpeg_banner(self, input_path):
        result = self.run_probe([self.ffmpeg_path.get(), "-hide_banner", "-i", input_path])
        if not result:
            return {}

        video_line = next((line.strip() for line in result.stderr.splitlines() if " Video:" in line), "")
        if not video_line:
            return {}

        info = {}
        size = re.search(r"\b(\d{3,5})x(\d{3,5})\b", video_line)
        if size:
            info["width"] = int(size.group(1))
            info["height"] = int(size.group(2))

        fps = re.search(r"\b([0-9]+(?:\.[0-9]+)?)\s+fps\b", video_line)
        tbr = re.search(r"\b([0-9]+(?:\.[0-9]+)?)\s+tbr\b", video_line)
        if fps:
            info["avg_frame_rate_text"] = fps.group(1)
        if tbr:
            info["r_frame_rate_text"] = tbr.group(1)

        self.parse_banner_color_group(video_line, info)
        return info

    @staticmethod
    def parse_banner_color_group(video_line, info):
        for group in re.findall(r"\(([^)]*)\)", video_line):
            group = group.strip().lower()
            if "/" not in group and not any(key in group for key in ("bt", "smpte", "arib")):
                continue

            range_part, color_part = ("", group)
            if "," in group:
                range_part, color_part = [part.strip() for part in group.split(",", 1)]

            if range_part in ("tv", "mpeg"):
                info["color_range"] = "tv"
            elif range_part in ("pc", "jpeg"):
                info["color_range"] = "pc"

            values = [value.strip() for value in color_part.split("/") if value.strip()]
            for key, value in zip(("color_space", "color_primaries", "color_transfer"), values):
                info[key] = value
            if any(info.get(k) for k in ("color_space", "color_primaries", "color_transfer")):
                return

    def output_standard(self):
        if int(self.video_size.get().split("x")[1]) >= 720:
            return {
                "label": "BT.709",
                "matrix_z": "709",
                "primaries_z": "709",
                "transfer_z": "709",
                "range_z": "limited",
                "matrix_ff": "bt709",
                "primaries_ff": "bt709",
                "transfer_ff": "bt709",
                "range_ff": "tv",
            }
        return {
            "label": "BT.601",
            "matrix_z": "170m",
            "primaries_z": "170m",
            "transfer_z": "601",
            "range_z": "limited",
            "matrix_ff": "smpte170m",
            "primaries_ff": "smpte170m",
            "transfer_ff": "smpte170m",
            "range_ff": "tv",
        }

    def fallback_input_standard(self, video_info):
        try:
            height = int(video_info.get("height", 0))
        except Exception:
            height = 0

        if height >= 2160:
            return {"matrix_z": "2020_ncl", "primaries_z": "2020", "transfer_z": "709", "range_z": "limited"}
        if height >= 720:
            return {"matrix_z": "709", "primaries_z": "709", "transfer_z": "709", "range_z": "limited"}
        return {"matrix_z": "170m", "primaries_z": "170m", "transfer_z": "601", "range_z": "limited"}

    def input_standard(self, video_info):
        fallback = self.fallback_input_standard(video_info)
        matrix = str(video_info.get("color_space", "")).lower() or "unknown"
        primaries = str(video_info.get("color_primaries", "")).lower() or "unknown"
        transfer = str(video_info.get("color_transfer", "")).lower() or "unknown"
        color_range = str(video_info.get("color_range", "")).lower() or "unknown"

        matrix_map = {
            "bt709": "709",
            "smpte170m": "170m",
            "bt470bg": "470bg",
            "fcc": "470bg",
            "smpte240m": "240m",
            "bt2020nc": "2020_ncl",
            "bt2020c": "2020_cl",
            "bt2020": "2020_ncl",
        }
        primaries_map = {
            "bt709": "709",
            "smpte170m": "170m",
            "bt470bg": "470bg",
            "smpte240m": "240m",
            "bt2020": "2020",
            "bt2020nc": "2020",
            "bt2020c": "2020",
        }
        transfer_map = {
            "bt709": "709",
            "smpte170m": "601",
            "bt470bg": "601",
            "smpte240m": "240m",
            "smpte2084": "smpte2084",
            "arib-std-b67": "arib-std-b67",
            "hlg": "arib-std-b67",
            "pq": "smpte2084",
        }
        range_map = {"pc": "full", "jpeg": "full", "full": "full", "tv": "limited", "mpeg": "limited", "limited": "limited"}

        return {
            "matrix_z": matrix_map.get(matrix, fallback["matrix_z"]),
            "primaries_z": primaries_map.get(primaries, fallback["primaries_z"]),
            "transfer_z": transfer_map.get(transfer, fallback["transfer_z"]),
            "range_z": range_map.get(color_range, fallback["range_z"]),
            "raw_matrix": video_info.get("color_space", "unknown"),
            "raw_primaries": video_info.get("color_primaries", "unknown"),
            "raw_transfer": video_info.get("color_transfer", "unknown"),
            "raw_range": video_info.get("color_range", "unknown"),
        }

    # ------------------------------------------------------------------ ffmpeg

    def target_size_for_filter(self):
        return ("720", "486") if self.video_size.get() == "720x480" else tuple(self.video_size.get().split("x"))

    def sar(self):
        return {
            ("1920x1080", "16:9"): "1/1",
            ("1920x1080", "4:3"): "3/4",
            ("1440x1080", "16:9"): "4/3",
            ("1440x1080", "4:3"): "1/1",
            ("1280x720", "16:9"): "1/1",
            ("1280x720", "4:3"): "3/4",
            ("720x480", "16:9"): "32/27",
            ("720x480", "4:3"): "8/9",
        }.get((self.video_size.get(), self.output_aspect.get()), "1/1")

    @staticmethod
    def parse_frame_rate(value):
        text = str(value or "").strip()
        if not text or text == "0/0":
            return None
        try:
            if "/" in text:
                num, den = text.split("/", 1)
                return float(num) / float(den) if float(den) else None
            return float(text)
        except Exception:
            return None

    def input_frame_rate(self, video_info):
        for value in (
            video_info.get("avg_frame_rate"),
            video_info.get("r_frame_rate"),
            video_info.get("avg_frame_rate_text"),
            video_info.get("r_frame_rate_text"),
        ):
            fps = self.parse_frame_rate(value)
            if fps and fps > 0:
                return fps
        return None

    def is_24000_1001(self, video_info):
        fps = self.input_frame_rate(video_info)
        return bool(fps and abs(fps - (24000 / 1001)) < 0.02)

    def video_rate_mode(self, video_info):
        if self.scan_mode.get() == "60p":
            return "fixed_60p"
        return "telecine_24p_to_60i" if self.is_24000_1001(video_info) else "fixed_60p_to_60i"

    def video_filter(self, video_info):
        width, height = self.target_size_for_filter()
        src = self.input_standard(video_info)
        dst = self.output_standard()
        parts = []

        if self.video_size.get() == "720x480":
            parts.extend([
                "drawbox=x=0:y=0:w=4:h=ih:color=black@1:t=fill",
                "drawbox=x=iw-4:y=0:w=4:h=ih:color=black@1:t=fill",
            ])

        parts.extend([
            (
                "zscale="
                f"w={width}:h={height}:"
                f"matrixin={src['matrix_z']}:primariesin={src['primaries_z']}:transferin={src['transfer_z']}:"
                f"rangein={src['range_z']}:"
                f"matrix={dst['matrix_z']}:primaries={dst['primaries_z']}:transfer={dst['transfer_z']}:range={dst['range_z']}"
            ),
            "format=yuv420p",
        ])

        if self.video_size.get().startswith("1440x"):
            parts.append("convolution=0 0 0 -0.25 1.5 -0.25 0 0 0")
        if self.video_size.get() == "720x480":
            parts.append("crop=720:480:0:4")

        mode = self.video_rate_mode(video_info)
        if mode == "fixed_60p":
            parts.extend(["fps=60000/1001", f"setsar={self.sar()}", "format=yuv420p"])
        elif mode == "telecine_24p_to_60i":
            parts.extend(["fps=24000/1001", "telecine=pattern=23", "setfield=tff", f"setsar={self.sar()}", "format=yuv420p"])
        else:
            parts.extend(["fps=60000/1001", "tinterlace=interleave_top", "setfield=tff", f"setsar={self.sar()}", "format=yuv420p"])

        parts.append(
            "setparams="
            f"colorspace={dst['matrix_ff']}:"
            f"color_primaries={dst['primaries_ff']}:"
            f"color_trc={dst['transfer_ff']}:"
            f"range={dst['range_ff']}"
        )
        return ",".join(parts)

    @staticmethod
    def audio_language_code(value):
        match = re.search(r"\(([a-z]{3})\)", str(value))
        if match:
            return match.group(1)
        text = str(value).strip()
        return text if len(text) == 3 else "jpn"

    def has_primary_external_audio(self):
        return self.primary_use_input_audio.get() != "on" and bool(self.primary_audio_path.get().strip())

    def has_secondary_audio(self):
        return self.audio_mode.get() != "Surround" and bool(self.secondary_audio_path.get().strip())

    def secondary_audio_channels(self):
        return "1" if self.secondary_audio_mode.get() == "Mono" else "2"

    def track_title(self, variable, fallback):
        return variable.get().strip() or fallback

    def ffmpeg_command(self, input_path, output_path, video_info):
        dst = self.output_standard()
        cmd = [self.ffmpeg_path.get(), "-y", "-hide_banner", "-i", input_path]

        primary_external = self.has_primary_external_audio()
        secondary_audio = self.has_secondary_audio()
        primary_audio_input = None
        secondary_audio_input = None
        next_input = 1

        if primary_external:
            primary_audio_input = next_input
            cmd.extend(["-i", self.primary_audio_path.get().strip()])
            next_input += 1
        if secondary_audio:
            secondary_audio_input = next_input
            cmd.extend(["-i", self.secondary_audio_path.get().strip()])

        cmd.extend(["-map", "0:v:0"])

        primary_mapped = False
        if self.primary_use_input_audio.get() == "on":
            cmd.extend(["-map", "0:a:0?"])
            primary_mapped = True
        elif primary_external:
            cmd.extend(["-map", f"{primary_audio_input}:a:0"])
            primary_mapped = True

        if secondary_audio:
            cmd.extend(["-map", f"{secondary_audio_input}:a:0"])

        cmd.extend([
            "-vf", self.video_filter(video_info),
            "-c:v", "mpeg2video",
            "-b:v", self.video_bitrate.get().strip() or "13M",
            "-maxrate", self.video_maxrate.get().strip() or "14M",
            "-bufsize", self.video_bufsize.get().strip() or "8M",
            "-g", self.gop.get().strip() or "15",
            "-bf", "2",
            "-pix_fmt", "yuv420p",
        ])

        if self.scan_mode.get() == "60i":
            cmd.extend(["-flags", "+ildct+ilme", "-r", "30000/1001"])
        else:
            cmd.extend(["-r", "60000/1001"])

        if self.is_ts_info_enabled():
            cmd.extend([
                "-mpegts_transport_stream_id", str(self.parse_number(self.transport_stream_id.get(), 1)),
                "-mpegts_original_network_id", str(self.parse_number(self.original_network_id.get(), 1)),
                "-mpegts_service_id", str(self.parse_number(self.service_id.get(), 1)),
                "-mpegts_service_type", "digital_tv",
                "-metadata", f"service_name={self.service_name_1.get().strip() or self.service_name.get().strip() or 'MakeTS'}",
                "-metadata", f"service_provider={self.provider_name.get().strip()}",
            ])

        audio_index = 0
        if primary_mapped:
            cmd.extend(self.audio_encode_args(
                audio_index,
                self.audio_bitrate.get().strip() or "256k",
                {"Mono": "1", "Stereo": "2", "Surround": "6"}.get(self.audio_mode.get(), "2"),
                self.primary_audio_language.get(),
                self.track_title(self.primary_audio_title, "Primary Audio"),
            ))
            audio_index += 1

        if secondary_audio:
            cmd.extend(self.audio_encode_args(
                audio_index,
                self.secondary_audio_bitrate.get().strip() or "256k",
                self.secondary_audio_channels(),
                self.secondary_audio_language.get(),
                self.track_title(self.secondary_audio_title, "Secondary Audio"),
                self.secondary_audio_samplerate.get(),
            ))

        cmd.extend([
            "-colorspace", dst["matrix_ff"],
            "-color_primaries", dst["primaries_ff"],
            "-color_trc", dst["transfer_ff"],
            "-mpegts_flags", "+resend_headers",
            "-muxrate", "8000k" if self.video_size.get() == "720x480" else "16000k",
            "-f", "mpegts",
            output_path,
        ])
        return cmd

    def audio_encode_args(self, index, bitrate, channels, language, title, sample_rate=None):
        return [
            f"-c:a:{index}", "aac",
            f"-b:a:{index}", bitrate,
            f"-ac:a:{index}", channels,
            f"-ar:a:{index}", (sample_rate or self.audio_samplerate.get()).strip() or "48000",
            f"-metadata:s:a:{index}", f"language={self.audio_language_code(language)}",
            f"-metadata:s:a:{index}", f"title={title}",
        ]

    # ------------------------------------------------------------------ XML

    def is_ts_info_enabled(self):
        return self.ts_info_enabled.get() == "on"

    def is_cat_enabled(self):
        return self.cat_enabled.get() == "on"

    def should_inject_eit(self):
        return self.eit_enabled.get() == "on"

    def is_program_info_enabled(self):
        return self.should_inject_eit() or self.tot_enabled.get() == "on"

    @staticmethod
    def parse_number(value, default=0):
        text = str(value).strip()
        if not text:
            return default
        try:
            return int(text, 0)
        except ValueError:
            return default

    def hex_value(self, value, digits=4):
        return f"0x{self.parse_number(value, 0):0{digits}X}"

    def ts_xml_values(self):
        service_name = self.service_name.get().strip() or "ＳＢＨ筑波"
        return {
            "service_name": xml_escape(service_name),
            "provider_name": xml_escape(self.provider_name.get().strip()),
            "network_name": xml_escape(self.network_name.get().strip() or "茨城７"),
            "ts_name": xml_escape(self.ts_name.get().strip() or service_name),
            "service_id": self.hex_value(self.service_id.get()),
            "oneseg_service_id": self.hex_value(self.oneseg_service_id.get()),
            "transport_stream_id": self.hex_value(self.transport_stream_id.get()),
            "original_network_id": self.hex_value(self.original_network_id.get()),
            "network_id": self.hex_value(self.network_id.get()),
            "remote_control_key_id": self.hex_value(self.remote_control_key_id.get(), 2),
            "service_type": self.hex_value(self.service_type.get(), 2),
        }

    @staticmethod
    def physical_channel_to_frequency_hz(channel):
        try:
            ch = int(str(channel).strip(), 0)
        except ValueError:
            return None
        if ch < 13 or ch > 62:
            return None
        return 473_142_857 + (ch - 13) * 6_000_000

    @staticmethod
    def format_tsduck_frequency(frequency_hz):
        return f"{int(frequency_hz):,}"

    def physical_channel_frequency_lines(self):
        lines = []
        used = set()
        for variable in self.physical_channels:
            frequency = self.physical_channel_to_frequency_hz(variable.get())
            if frequency is None or frequency in used:
                continue
            used.add(frequency)
            lines.append(f'        <frequency value="{self.format_tsduck_frequency(frequency)}"/>')
        return lines

    def cat_private_data_lines(self):
        hex_text = re.sub(r"[^0-9A-Fa-f]", "", self.cat_private_data.get().strip()).upper() or "01"
        if len(hex_text) % 2:
            hex_text = "0" + hex_text
        return ["        " + " ".join(hex_text[i:i + 2] for i in range(0, len(hex_text), 2))]

    def write_cat_xml_file(self, base_name):
        path = os.path.join(tempfile.gettempdir(), base_name + "_cat.xml")
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            "<tsduck>",
            f'  <CAT version="{self.parse_number(self.cat_version.get(), 11)}" current="true">',
            '    <metadata PID="1"/>',
            (
                f'    <ISDB_access_control_descriptor '
                f'CA_system_id="{self.hex_value(self.cat_ca_system_id.get())}" '
                f'transmission_type="{self.parse_number(self.cat_transmission_type.get(), 7)}" '
                f'PID="{self.hex_value(self.cat_pid.get())}">'
            ),
            "      <private_data>",
            *self.cat_private_data_lines(),
            "      </private_data>",
            "    </ISDB_access_control_descriptor>",
            "  </CAT>",
            "</tsduck>",
            "",
        ]
        return self.write_temp_xml(path, lines)

    def write_tsduck_xml_files(self, base_name):
        values = self.ts_xml_values()
        sdt_path = os.path.join(tempfile.gettempdir(), base_name + "_sdt.xml")
        nit_path = os.path.join(tempfile.gettempdir(), base_name + "_nit.xml")

        service_ids = self.service_ids()
        service_names = [
            xml_escape(self.service_name_1.get().strip() or (self.service_name.get().strip() + "・１")),
            xml_escape(self.service_name_2.get().strip() or (self.service_name.get().strip() + "・２")),
            xml_escape(self.service_name_3.get().strip() or (self.service_name.get().strip() + "・３")),
            xml_escape(self.service_name_1seg.get().strip() or (self.service_name.get().strip() + "携帯１")),
        ]
        provider = xml_escape(self.provider_name.get().strip())

        sdt_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            "<tsduck>",
            f'  <SDT version="0" current="true" transport_stream_id="{values["transport_stream_id"]}" original_network_id="{values["original_network_id"]}" actual="true">',
            '    <metadata PID="17"/>',
        ]
        for service_id, service_name, service_type, user_defined, eit_schedule in [
            (service_ids[0], service_names[0], "0x01", "4", "true"),
            (service_ids[1], service_names[1], "0x01", "4", "true"),
            (service_ids[2], service_names[2], "0x01", "4", "true"),
            (service_ids[3], service_names[3], "0xC0", "11", "false"),
        ]:
            sdt_lines.extend([
                f'    <service service_id="{service_id}" EIT_schedule="{eit_schedule}" EIT_present_following="true" CA_mode="false" running_status="undefined">',
                f'      <service_descriptor service_type="{service_type}" service_provider_name="{provider}" service_name="{service_name}"/>',
                f'      <digital_copy_control_descriptor digital_recording_control_data="2" user_defined="{user_defined}"/>',
                "    </service>",
            ])
        sdt_lines.extend(["  </SDT>", "</tsduck>", ""])

        nit_lines = self.nit_xml_lines(values, service_ids)
        self.write_temp_xml(sdt_path, sdt_lines)
        self.write_temp_xml(nit_path, nit_lines)
        return sdt_path, nit_path

    def service_ids(self):
        base = self.parse_number(self.service_id.get(), 0x6238)
        return [f"0x{base + offset:04X}" for offset in range(3)] + [self.hex_value(self.oneseg_service_id.get())]

    def nit_xml_lines(self, values, service_ids):
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            "<tsduck>",
            f'  <NIT version="11" current="true" network_id="{values["network_id"]}" actual="true">',
            '    <metadata PID="16"/>',
            f'    <network_name_descriptor network_name="{values["network_name"]}"/>',
            '    <system_management_descriptor broadcasting_flag="0" broadcasting_identifier="0x03" additional_broadcasting_identification="0x01"/>',
            f'    <transport_stream transport_stream_id="{values["transport_stream_id"]}" original_network_id="{values["original_network_id"]}" preferred_section="0">',
            "      <service_list_descriptor>",
            f'        <service service_id="{service_ids[0]}" service_type="0x01"/>',
            f'        <service service_id="{service_ids[1]}" service_type="0x01"/>',
            f'        <service service_id="{service_ids[2]}" service_type="0x01"/>',
            f'        <service service_id="{service_ids[3]}" service_type="0xC0"/>',
            "      </service_list_descriptor>",
        ]

        frequency_lines = self.physical_channel_frequency_lines()
        if frequency_lines:
            lines.extend([
                '      <ISDB_terrestrial_delivery_system_descriptor area_code="0x0C69" guard_interval="1/8" transmission_mode="8k">',
                *frequency_lines,
                "      </ISDB_terrestrial_delivery_system_descriptor>",
            ])

        lines.extend([
            "      <partial_reception_descriptor>",
            f'        <service id="{service_ids[3]}"/>',
            "      </partial_reception_descriptor>",
            f'      <TS_information_descriptor remote_control_key_id="{values["remote_control_key_id"]}" ts_name="{values["ts_name"]}">',
            '        <transmission_type transmission_type_info="0x0F">',
            f'          <service id="{service_ids[0]}"/>',
            f'          <service id="{service_ids[1]}"/>',
            f'          <service id="{service_ids[2]}"/>',
            "        </transmission_type>",
            '        <transmission_type transmission_type_info="0xAF">',
            f'          <service id="{service_ids[3]}"/>',
            "        </transmission_type>",
            "      </TS_information_descriptor>",
            "    </transport_stream>",
            "  </NIT>",
            "</tsduck>",
            "",
        ])
        return lines

    def genre_nibbles(self):
        match = re.search(r"\((0x[0-9A-Fa-f]+)/(0x[0-9A-Fa-f]+)\)", self.genre.get())
        return match.groups() if match else ("0x0", "0x0")

    def normalize_eit_datetime(self, text):
        text = text.strip()
        if not text:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d:%H:%M:%S"):
            try:
                return datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
        return text

    def normalize_timeref_datetime(self, text):
        text = text.strip()
        if not text:
            return "system"
        for fmt in ("%Y/%m/%d:%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
            try:
                return datetime.strptime(text, fmt).strftime("%Y/%m/%d:%H:%M:%S")
            except ValueError:
                pass
        return text

    def program_time_value(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S") if self.tot_time_source.get() == "system" else self.normalize_eit_datetime(self.tot_start_time.get())

    def timeref_start_value(self):
        return "system" if self.tot_time_source.get() == "system" else self.normalize_timeref_datetime(self.tot_start_time.get())

    def get_event_description(self):
        if self.description_text is None:
            return self.event_text.get().strip()
        return self.description_text.get("1.0", "end-1c").strip()

    def write_program_xml_files(self, base_name):
        eit_path = os.path.join(tempfile.gettempdir(), base_name + "_eit.xml")
        time_path = os.path.join(tempfile.gettempdir(), base_name + "_tot.xml")

        values = self.ts_xml_values()
        content_l1, content_l2 = self.genre_nibbles()

        eit_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            "<tsduck>",
            f'  <EIT type="pf" version="0" current="true" actual="true" service_id="{self.hex_value(self.service_id.get())}" transport_stream_id="{values["transport_stream_id"]}" original_network_id="{values["original_network_id"]}" last_table_id="0x4E">',
            '    <metadata PID="18"/>',
            f'    <event event_id="{self.hex_value(self.event_id.get())}" start_time="{self.normalize_eit_datetime(self.event_start_time.get())}" duration="{self.event_duration.get().strip() or "00:15:00"}" running_status="{self.event_running_status.get().strip() or "running"}" CA_mode="false">',
            f'      <short_event_descriptor language_code="{self.audio_language_code(self.event_language.get())}">',
            f"        <event_name>{xml_escape(self.event_name.get().strip() or 'Program')}</event_name>",
            f"        <text>{xml_escape(self.get_event_description())}</text>",
            "      </short_event_descriptor>",
            '      <component_descriptor stream_content="0x01" stream_content_ext="0x0F" component_type="0xB3" component_tag="0x00" language_code="jpn" text=""/>',
            "      <content_descriptor>",
            f'        <content content_nibble_level_1="{content_l1}" content_nibble_level_2="{content_l2}" user_byte="0x00"/>',
            "      </content_descriptor>",
            "    </event>",
            "  </EIT>",
            "</tsduck>",
            "",
        ]

        time_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            "<tsduck>",
            f'  <TOT UTC_time="{self.program_time_value()}"/>',
            "</tsduck>",
            "",
        ]

        self.write_temp_xml(eit_path, eit_lines)
        self.write_temp_xml(time_path, time_lines)
        return eit_path, time_path

    @staticmethod
    def write_temp_xml(path, lines):
        with open(path, "w", encoding="utf-8") as file:
            file.write("\n".join(lines))
        return path

    def tsduck_command(self, input_path, output_path, sdt_path, nit_path, cat_path=None, eit_path=None, time_path=None):
        cmd = [self.tsduck_path.get().strip() or "tsp", "-I", "file", input_path]

        if self.is_cat_enabled() and cat_path:
            cmd.extend(["-P", "inject", cat_path, "--japan", "--pid", "0x0001", "--replace"])

        cmd.extend([
            "-P", "inject", sdt_path, "--japan", "--pid", "0x0011", "--replace",
            "-P", "inject", nit_path, "--japan", "--pid", "0x0010", "--bitrate", "15000",
        ])

        if self.eit_enabled.get() == "on" and eit_path:
            cmd.extend(["-P", "inject", eit_path, "--japan", "--pid", "0x0012", "--bitrate", "50000"])

        if self.tot_enabled.get() == "on" and time_path:
            cmd.extend([
                "-P", "inject", time_path, "--japan", "--stuffing", "--pid", "0x0014", "--bitrate", "15000",
                "-P", "timeref", "--start", self.timeref_start_value(), "--local-time-offset", "540", "--next-time-offset", "540",
            ])

        cmd.extend(["-O", "file", output_path])
        return cmd

    # ------------------------------------------------------------------ run

    def run_command_with_log(self, cmd):
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

        assert self.process.stdout is not None
        for line in self.process.stdout:
            self.log_queue.put(line)

        return_code = self.process.wait()
        self.process = None
        return return_code

    def start_encode(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return

        if not self.input_files:
            messagebox.showwarning(self.t("No input"), self.t("Add files first."))
            return

        output_path = self.output_path.get().strip()
        if output_path:
            output_dir = os.path.dirname(os.path.abspath(output_path))
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status.set(self.t("Encoding"))
        self.tabs.select(self.log_tab)
        self.write_log("=== Encode start ===\n")

        self.worker_thread = threading.Thread(target=self.encode_worker, daemon=True)
        self.worker_thread.start()

    def encode_worker(self):
        try:
            input_files = list(self.input_files)
            total_files = len(input_files)

            for file_index, input_path in enumerate(input_files, start=1):
                if not self.encode_one_file(input_path, file_index, total_files):
                    break
            self.log_queue.put("\n=== Encode finished ===\n")
        except FileNotFoundError:
            self.log_queue.put("\n" + self.t("ffmpeg, ffprobe, or tsp was not found. Check paths.") + "\n")
        except Exception as exc:
            self.log_queue.put(f"\nError: {exc}\n")
        finally:
            self.log_queue.put("__ENCODE_DONE__")

    def output_folder_for_input(self, input_path):
        save_path = self.output_path.get().strip()
        if save_path:
            folder = os.path.dirname(os.path.abspath(save_path))
            if folder:
                return folder
        return os.path.dirname(os.path.abspath(input_path)) or os.getcwd()

    def output_filename_for_input(self, input_path, file_index=1, total_files=1):
        save_path = self.output_path.get().strip()
        if save_path:
            name = os.path.basename(save_path)
            stem, ext = os.path.splitext(name)
            if not stem:
                stem = os.path.splitext(os.path.basename(input_path))[0] + "_mpeg2ts"
            if not ext:
                ext = ".ts"
            if total_files > 1:
                return f"{stem}_{file_index}{ext}"
            return stem + ext

        base = os.path.splitext(os.path.basename(input_path))[0]
        return base + "_mpeg2ts.ts"

    def encode_one_file(self, input_path, file_index=1, total_files=1):
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_dir = self.output_folder_for_input(input_path)
        os.makedirs(output_dir, exist_ok=True)

        output_name = self.output_filename_for_input(input_path, file_index, total_files)
        final_output = os.path.join(output_dir, output_name)

        final_stem, final_ext = os.path.splitext(output_name)
        work_name = final_stem + "_work" + (final_ext or ".ts")
        ffmpeg_output = os.path.join(output_dir, work_name) if self.is_ts_info_enabled() else final_output

        video_info = self.probe_video_info(input_path)
        ffmpeg_cmd = self.ffmpeg_command(input_path, ffmpeg_output, video_info)
        self.log_encode_settings(input_path, final_output, video_info, ffmpeg_cmd)

        if self.run_command_with_log(ffmpeg_cmd) != 0:
            self.log_queue.put("\nFFmpeg failed\n")
            return False

        if self.is_ts_info_enabled():
            return self.run_tsduck(base, ffmpeg_output, final_output)

        self.log_queue.put("\nDone\n")
        return True

    def run_tsduck(self, base, ffmpeg_output, final_output):
        sdt_path, nit_path = self.write_tsduck_xml_files(base)
        cat_path = self.write_cat_xml_file(base) if self.is_cat_enabled() else None
        eit_path = time_path = None

        if self.is_program_info_enabled():
            eit_path, time_path = self.write_program_xml_files(base)

        if os.path.exists(final_output):
            try:
                os.remove(final_output)
            except OSError:
                pass

        cmd = self.tsduck_command(ffmpeg_output, final_output, sdt_path, nit_path, cat_path, eit_path, time_path)
        self.log_tsduck_files(cmd, sdt_path, nit_path, cat_path, eit_path, time_path)

        if self.run_command_with_log(cmd) != 0:
            self.log_queue.put("\nTSDuck failed\n")
            return False

        try:
            if os.path.exists(ffmpeg_output):
                os.remove(ffmpeg_output)
        except OSError:
            pass

        self.log_queue.put("\nDone\n")
        return True

    def log_encode_settings(self, input_path, output_path, video_info, cmd):
        src = self.input_standard(video_info)
        dst = self.output_standard()
        fps = self.input_frame_rate(video_info)

        self.log_queue.put(f"\nSource: {input_path}\n")
        self.log_queue.put(f"Output: {output_path}\n")
        self.log_queue.put(
            f"Video: {self.video_size.get()} / {self.scan_mode.get()} / {self.output_aspect.get()} / "
            f"bitrate {self.video_bitrate.get()} / maxrate {self.video_maxrate.get()} / bufsize {self.video_bufsize.get()}\n"
        )
        self.log_queue.put(
            "Input color: "
            f"matrix={src['raw_matrix']} -> {src['matrix_z']}, "
            f"primaries={src['raw_primaries']} -> {src['primaries_z']}, "
            f"transfer={src['raw_transfer']} -> {src['transfer_z']}, "
            f"range={src['raw_range']} -> {src['range_z']}\n"
        )
        self.log_queue.put(
            f"Output color: {dst['label']} matrix={dst['matrix_z']}, "
            f"primaries={dst['primaries_z']}, transfer={dst['transfer_z']}\n"
        )
        fps_text = f"{fps:.3f}" if fps else "unknown"
        self.log_queue.put(f"Input frame rate: {fps_text} / Video rate process: {self.video_rate_mode(video_info)}\n")

        primary_source = "input audio" if self.primary_use_input_audio.get() == "on" else (self.primary_audio_path.get().strip() or "none")
        self.log_queue.put(
            f"Primary audio: {primary_source} / AAC / {self.audio_mode.get()} / "
            f"{self.audio_bitrate.get()} / {self.audio_samplerate.get()} Hz / "
            f"{self.audio_language_code(self.primary_audio_language.get())} / title={self.track_title(self.primary_audio_title, 'Primary Audio')}\n"
        )

        if self.has_secondary_audio():
            self.log_queue.put(
                f"Secondary audio: {self.secondary_audio_path.get().strip()} / {self.secondary_audio_mode.get()} / "
                f"{self.secondary_audio_bitrate.get()} / {self.secondary_audio_samplerate.get()} Hz / "
                f"{self.audio_language_code(self.secondary_audio_language.get())} / "
                f"title={self.track_title(self.secondary_audio_title, 'Secondary Audio')}\n"
            )

        if self.video_size.get() == "720x480":
            self.log_queue.put("SD process: blacken L/R 4px -> scale 720x486 -> crop 720x480\nMuxrate: 8000k\n")
        else:
            if self.video_size.get().startswith("1440x"):
                self.log_queue.put("Resize sharpen: quarter-strength horizontal-only convolution sharpen for 1440-wide output\n")
            self.log_queue.put("Muxrate: 16000k\n")

        self.log_queue.put("FFmpeg command:\n" + subprocess.list2cmdline(cmd) + "\n\n")

    def log_tsduck_files(self, cmd, sdt_path, nit_path, cat_path, eit_path, time_path):
        self.log_queue.put("\nTSDuck XML:\n")
        if cat_path:
            self.log_queue.put(f"CAT: {cat_path}\n")
        self.log_queue.put(f"SDT: {sdt_path}\n")
        self.log_queue.put(f"NIT: {nit_path}\n")
        if eit_path:
            self.log_queue.put(f"EIT: {eit_path}\n")
        if time_path:
            self.log_queue.put(f"TOT: {time_path}\n")
            self.log_queue.put(f"TOT time: dynamic progression via timeref / start={self.timeref_start_value()} / inject=--stuffing\n")
        self.log_queue.put("TSDuck command:\n" + subprocess.list2cmdline(cmd) + "\n\n")

    def stop_encode(self):
        if self.process and self.process.poll() is None:
            self.write_log("\n" + self.t("Stop requested") + "\n")
            self.process.terminate()

    def poll_log_queue(self):
        try:
            while True:
                message = self.log_queue.get_nowait()
                if message == "__ENCODE_DONE__":
                    self.start_button.config(state="normal")
                    self.stop_button.config(state="disabled")
                    self.status.set(self.t("Ready"))
                else:
                    self.write_log(message)
        except queue.Empty:
            pass

        self.after(100, self.poll_log_queue)

    def write_log(self, message):
        self.log.insert("end", message)
        self.log.see("end")


if __name__ == "__main__":
    app = MakeTSGui()
    app.mainloop()
