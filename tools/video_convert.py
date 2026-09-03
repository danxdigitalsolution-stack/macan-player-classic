import sys, os, re, time, subprocess, base64
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QProgressBar,
    QComboBox, QMessageBox, QCheckBox, QFrame, QStackedWidget,
    QSpinBox, QScrollArea
)
from PySide6.QtCore import QThread, QObject, Signal, QProcess, QSettings, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

def _make_hidden_qprocess():
    """Bikin QProcess yg gak nampilin jendela console ffmpeg/ffprobe pas
    di-spawn di Windows (tanpa ini, tiap panggilan ffmpeg bakal keliatan
    flash jendela CLI hitam sekilas, mirip bug lama di Macan Movie Pro).
    Di platform lain (Linux/macOS) gak ada konsep console window kayak gini,
    jadi cukup return QProcess biasa."""
    process = QProcess()
    if os.name == 'nt':
        CREATE_NO_WINDOW = 0x08000000
        def _modifier(args):
            args.flags |= CREATE_NO_WINDOW
        process.setCreateProcessArgumentsModifier(_modifier)
    return process


def _probe_duration_fps(ffmpeg_path, input_path, need_fps=True):
    """Ambil (duration_sec, fps) video pakai ffmpeg yg ada di root project
    (spawn `ffmpeg -i` lewat QProcess lalu regex-parsing teks stderr-nya).
    duration_sec dibalikin sbg int (detik bulat) spy kompatibel sama
    pemakaian lama (range(total_seconds), dst).

    need_fps=False dipakai pemanggil yg cuma butuh durasi (mis. progress bar
    konversi)."""
    duration_regex = re.compile(r"Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})")
    fps_regex = re.compile(r"(\d+(?:\.\d+)?)\s+fps")
    process = _make_hidden_qprocess()
    process.start(ffmpeg_path, ['-i', input_path])
    if not process.waitForFinished(8000):
        process.kill()
        return None, None
    output = bytes(process.readAllStandardError()).decode('utf-8', 'ignore')
    output += bytes(process.readAllStandardOutput()).decode('utf-8', 'ignore')
    duration_sec = None; fps = None
    dur_match = duration_regex.search(output)
    if dur_match:
        h, m, s, cs = map(int, dur_match.groups())
        duration_sec = h * 3600 + m * 60 + s
    fps_match = fps_regex.search(output)
    if fps_match:
        fps = float(fps_match.group(1))
    return duration_sec, fps


# --- SVG ICONS (Embedded) ---
SVG_ICONS = {
    "video": "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZHRoPSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxyZWN0IHg9IjIiIHk9IjIiIHdpZHRoPSIyMCIgaGVpZ2h0PSIyMCIgcng9IjIuMTgiIHJ5PSIyLjE4Ij48L3JlY3Q+PGxpbmUgeDE9IjciIHkxPSIyIiB4Mj0iNyIgeTI9IjIyIj48L2xpbmU+PGxpbmUgeDE9IjE3IiB5MT0iMiIgeDI9IjE3IiB5Mj0iMjIiPjwvbGluZT48bGluZSB4MT0iMiIgeTE9IjEyIiB4Mj0iMjIiIHkyPSIxMiI+PC9saW5lPjxsaW5lIHgxPSIyIiB5MT0iNyIgeDI9IjciIHkyPSI3Ij48L2xpbmU+PGxpbmUgeDE9IjIiIHkxPSIxNyIgeDI9IjciIHkyPSIxNyI+PC9saW5lPjxsaW5lIHgxPSIxNyIgeTE9IjE3IiB4Mj0iMjIiIHkyPSIxNyI+PC9saW5lPjxsaW5lIHgxPSIxNyIgeTE9IjciIHgyPSIyMiIgeTI9IjeiPjwvbGluZT48L3N2Zz4=",
    "folder": "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZHRoPSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwYXRoIGQ9Ik0yMiAxOWEyIDIgMCAwIDEtMiAySDRhMiAyIDAgMCAxLTItMlY1YTIgMiAwIDAgMSAyLTJoNWwyIDNoOWEyIDIgMCAwIDEgMiAyeiI+PC9wYXRoPjwvc3ZnPg==",
    "browse": "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZHRoPSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxjaXJjbGUgY3g9IjExIiBjeT0iMTEiIHI9IjgiPjwvY2lyY2xlPjxsaW5lIHgxPSIyMSIgeTE9IjIxIiB4Mj0iMTYuNjUiIHkyPSIxNi42NSI+PC9saW5lPjwvc3ZnPg==",
    "play": "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZHRoPSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwb2x5Z29uIHBvaW50cz0iNSAzIDE5IDEyIDUgMjEgNSAzIj48L3BvbHlnb24+PC9zdmc+",
    "stop": "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZHRoPSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxyZWN0IHg9IjMiIHk9IjMiIHdpZHRoPSIxOCIgaGVpZ2h0PSIxOCIgcng9IjIiIHJ5PSIyIj48L3JlY3Q+PC9zdmc+"
}

def get_icon_from_svg(svg_data_base64, color="#E0E0E0"):
    try:
        svg_data_str = base64.b64decode(svg_data_base64).decode('utf-8')
        svg_data_colored = svg_data_str.replace('currentColor', color)
        renderer = QSvgRenderer(svg_data_colored.encode('utf-8'))
        pixmap = QPixmap(renderer.defaultSize())
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return QIcon(pixmap)
    except: return QIcon()

# --- LANGUAGES ---
LANGUAGES = {
    "id": {
        "input_vid_label": "1. Input Video",
        "output_label": "2. Output Folder",
        "vid_options_label": "3. Opsi Konversi",
        "browse_btn": "Browse...",
        "clear_list_btn": "Bersihkan",
        "start_conversion_btn": "Mulai Konversi",
        "stop_conversion_btn": "Hentikan",
        "batch_mode_checkbox": "Batch Mode",
        "output_format_label": "Format:",
        "resolution_label": "Resolusi:",
        "quality_label": "Kualitas:",
        "ready_status": "Siap.",
        "converting_progress": "Mengonversi... {progress}%",
        "eta_label": "Sisa: {time}",
        "done": "Selesai!",
        "error_title": "Error",
        "invalid_input_title": "Input Tidak Valid",
        "invalid_output_folder_msg": "Silakan pilih folder output yang valid.",
        "batch_no_files_msg": "Silakan pilih setidaknya satu file video.",
        "ffmpeg_not_found_title": "FFmpeg Tidak Ditemukan",
        "ffmpeg_not_found_msg": "ffmpeg tidak ditemukan di direktori aplikasi atau di system PATH.",
        "ffmpeg_failed_to_start": "Gagal memulai proses ffmpeg.",
        "ffmpeg_failed_with_code": "Konversi ffmpeg gagal. Kode keluar: {code}\nError: {error}",
        "conversion_stopped": "Konversi dihentikan oleh pengguna.",
        "getting_video_info": "Mendapatkan info video...",
        "video_conversion_success": "Sukses! Video telah dikonversi ke {format}.",
        "preparing_conversion": "Mempersiapkan konversi untuk {filename}...",
        "converting_batch_file": "Mengonversi file {current} dari {total}: {filename}",
        "batch_complete_title": "Batch Selesai",
        "batch_complete_msg": "Batch selesai! Semua {count} file telah berhasil dikonversi.",
        "vid_formats": ["mp4", "mkv", "avi", "mov", "webm", "ts", "flv", "wmv", "3gp", "m4v", "ogv", "vob", "divx", "f4v", "gif", "jpg (Frame)", "png (Frame)"],
        "vid_qualities": ["Tinggi", "Sedang", "Rendah"],

        # Frame extraction
        "frame_extract_mode_label": "Mode Ekstraksi Frame:",
        "frame_extract_mode_per_sec": "1 frame/detik (frame terakhir tiap detik)",
        "frame_extract_mode_all": "Semua Frame (setiap frame)",
        "frame_extract_progress": "Mengekstrak frame detik ke-{sec} dari {total}...",
        "frame_extract_success": "Sukses! {count} frame telah diekstrak ke folder '{folder}'.",
        "frame_extract_all_progress": "Mengekstrak frame {current} dari ~{total}...",
        "frame_extract_all_success": "Sukses! {count} frame telah diekstrak ke folder '{folder}'.",

        # Advanced options
        "advanced_checkbox": "Opsi Lanjutan",
        "gpu_checkbox": "GPU Rendering (NVENC)",
        "video_bitrate_label": "Video Bitrate:",
        "fps_label": "FPS:",
        "video_encoder_label": "Video Encoder:",
        "audio_encoder_label": "Audio Encoder:",
        "channels_label": "Channels:",
        "sample_rate_label": "Sample Rate:",
        "audio_bitrate_label": "Audio Bitrate:",
        "ref_frames_label": "Ref Frames:",
        "cabac_label": "Gunakan CABAC",
        "custom_flags_label": "Custom Flags FFmpeg:",

        # Subtitle
        "subtitle_label": "Subtitle (Opsional):",
        "subtitle_btn": "Pilih File Subtitle...",
        "subtitle_mode_label": "Mode Subtitle:",
        "subtitle_modes": ["Tidak Ada", "Burn-in (Hardcode)", "Embed (Softcode, MKV)"],
        "subtitle_no_file": "Tidak ada file subtitle dipilih.",
    },
    "en": {
        "input_vid_label": "1. Input Video",
        "output_label": "2. Output Folder",
        "vid_options_label": "3. Conversion Options",
        "browse_btn": "Browse...",
        "clear_list_btn": "Clear",
        "start_conversion_btn": "Start Conversion",
        "stop_conversion_btn": "Stop",
        "batch_mode_checkbox": "Batch Mode",
        "output_format_label": "Format:",
        "resolution_label": "Resolution:",
        "quality_label": "Quality:",
        "ready_status": "Ready.",
        "converting_progress": "Converting... {progress}%",
        "eta_label": "ETA: {time}",
        "done": "Done!",
        "error_title": "Error",
        "invalid_input_title": "Invalid Input",
        "invalid_output_folder_msg": "Please select a valid output folder.",
        "batch_no_files_msg": "Please select at least one video file.",
        "ffmpeg_not_found_title": "FFmpeg Not Found",
        "ffmpeg_not_found_msg": "ffmpeg was not found in the application directory or in the system PATH.",
        "ffmpeg_failed_to_start": "Failed to start ffmpeg process.",
        "ffmpeg_failed_with_code": "ffmpeg conversion failed. Exit code: {code}\nError: {error}",
        "conversion_stopped": "Conversion stopped by user.",
        "getting_video_info": "Getting video info...",
        "video_conversion_success": "Success! The video has been converted to {format}.",
        "preparing_conversion": "Preparing conversion for {filename}...",
        "converting_batch_file": "Converting file {current} of {total}: {filename}",
        "batch_complete_title": "Batch Complete",
        "batch_complete_msg": "Batch finished! All {count} files have been successfully converted.",
        "vid_formats": ["mp4", "mkv", "avi", "mov", "webm", "ts", "flv", "wmv", "3gp", "m4v", "ogv", "vob", "divx", "f4v", "gif", "jpg (Frame)", "png (Frame)"],
        "vid_qualities": ["High", "Medium", "Low"],

        # Frame extraction
        "frame_extract_mode_label": "Frame Extraction Mode:",
        "frame_extract_mode_per_sec": "1 frame/sec (last frame of each second)",
        "frame_extract_mode_all": "All Frames (every frame)",
        "frame_extract_progress": "Extracting frame for second {sec} of {total}...",
        "frame_extract_success": "Success! {count} frames extracted to folder '{folder}'.",
        "frame_extract_all_progress": "Extracting frame {current} of ~{total}...",
        "frame_extract_all_success": "Success! {count} frames extracted to folder '{folder}'.",

        # Advanced options
        "advanced_checkbox": "Advanced Options",
        "gpu_checkbox": "GPU Rendering (NVENC)",
        "video_bitrate_label": "Video Bitrate:",
        "fps_label": "FPS:",
        "video_encoder_label": "Video Encoder:",
        "audio_encoder_label": "Audio Encoder:",
        "channels_label": "Channels:",
        "sample_rate_label": "Sample Rate:",
        "audio_bitrate_label": "Audio Bitrate:",
        "ref_frames_label": "Ref Frames:",
        "cabac_label": "Use CABAC",
        "custom_flags_label": "Custom FFmpeg Flags:",

        # Subtitle
        "subtitle_label": "Subtitle (Optional):",
        "subtitle_btn": "Select Subtitle File...",
        "subtitle_mode_label": "Subtitle Mode:",
        "subtitle_modes": ["None", "Burn-in (Hardcode)", "Embed (Softcode, MKV)"],
        "subtitle_no_file": "No subtitle file selected.",
    }
}


# =============================================================================
# WORKER — Konversi Video (lengkap: GPU/NVENC, encoder, bitrate, fps, audio,
# subtitle burn-in/embed, custom flags, ref frames, CABAC)
# Diporting dari macan_converter (VideoConversionWorker)
# =============================================================================
class VideoConversionWorker(QObject):
    progress_updated = Signal(int, str)
    conversion_finished = Signal(str)
    conversion_error = Signal(str)

    def __init__(self, ffmpeg_path, input_path, output_path, out_format,
                 resolution, quality, lang_dict=None,
                 is_advanced=False, use_gpu=False,
                 v_bitrate="Auto", fps="Original", v_encoder="libx264 (H.264)",
                 a_encoder="aac", a_channels="Original", a_samplerate="Original", a_bitrate="Original",
                 custom_flags="", ref_frames=0, use_cabac=True,
                 subtitle_path="", subtitle_mode="Tidak Ada"):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path; self.input_path = input_path; self.output_path = output_path
        self.out_format = out_format; self.resolution = resolution; self.quality = quality
        self.is_running = True; self.lang = lang_dict if lang_dict else LANGUAGES["id"]

        self.is_advanced = is_advanced
        self.use_gpu = use_gpu
        self.v_bitrate = v_bitrate
        self.fps = fps
        self.v_encoder = v_encoder.split(' ')[0]   # 'libx264 (H.264)' -> 'libx264'
        self.a_encoder = a_encoder.split(' ')[0]   # 'libmp3lame (MP3)' -> 'libmp3lame'
        self.a_channels = a_channels.split(' ')[0]  # '1 (Mono)' -> '1'
        self.a_samplerate = a_samplerate
        self.a_bitrate = a_bitrate

        self.custom_flags = custom_flags
        self.ref_frames = ref_frames
        self.use_cabac = use_cabac

        self.subtitle_path = subtitle_path
        self.subtitle_mode = subtitle_mode  # "Tidak Ada"/"None" / "Burn-in (Hardcode)" / "Embed (Softcode, MKV)"

        self.process = None
        self.time_regex = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
        self.total_duration = None
        self._stderr_buffer = ""
        self._conversion_start_time = None

    def _get_media_duration(self):
        duration_sec, _fps = _probe_duration_fps(self.ffmpeg_path, self.input_path, need_fps=False)
        return duration_sec

    def run(self):
        self._stderr_buffer = ""
        base_name = os.path.splitext(os.path.basename(self.input_path))[0]
        output_filename = os.path.join(self.output_path, f"{base_name}.{self.out_format}")

        command_args = []

        # --- 1. Hardware Acceleration (CUDA) ---
        if self.use_gpu:
            command_args.extend(['-hwaccel', 'cuda'])

        command_args.extend(['-i', self.input_path])

        # --- 2. Resolusi (Scaling) ---
        resolution_map = {"360p": "360", "480p": "480", "720p": "720", "1080p": "1080", "2K": "1440", "4K": "2160"}
        if self.resolution in resolution_map:
            target_height = resolution_map[self.resolution]
            if self.use_gpu:
                command_args.extend(['-vf', f'scale_cuda=-2:{target_height}'])
            else:
                command_args.extend(['-vf', f'scale=-2:{target_height}'])

        # --- 3. Penentuan Encoder Video ---
        final_v_encoder = "libx264"
        if self.is_advanced:
            final_v_encoder = self.v_encoder
        else:
            if self.out_format in ["mp4", "mov", "mkv", "ts", "flv", "3gp", "m4v", "divx", "f4v"]:
                final_v_encoder = "libx264"
            elif self.out_format in ["wmv"]:
                final_v_encoder = "wmv2"
            elif self.out_format in ["vob"]:
                final_v_encoder = "mpeg2video"
            elif self.out_format in ["ogv"]:
                final_v_encoder = "libtheora"
            elif self.out_format in ["webm"]:
                final_v_encoder = "libvpx-vp9"

        # Override encoder jika GPU aktif (NVIDIA NVENC)
        gpu_compatible_formats = ["mp4", "mkv", "mov", "ts", "flv", "3gp", "m4v", "f4v"]
        if self.use_gpu and self.out_format in gpu_compatible_formats:
            if "libx264" in final_v_encoder or "h264" in final_v_encoder:
                final_v_encoder = "h264_nvenc"
            elif "libx265" in final_v_encoder or "h265" in final_v_encoder:
                final_v_encoder = "hevc_nvenc"

        # --- 4. Parameter Encoder Video ---
        if final_v_encoder != "copy":
            command_args.extend(['-c:v', final_v_encoder])

            # A. Bitrate / CRF
            if self.is_advanced:
                bitrate_val = str(self.v_bitrate).strip()
                if bitrate_val and bitrate_val != "Auto":
                    if bitrate_val.isdigit():
                        bitrate_val += "k"
                    if any(char.isdigit() for char in bitrate_val):
                        command_args.extend(['-b:v', bitrate_val])
                        if self.use_gpu:
                            command_args.extend(['-maxrate', bitrate_val])
                            try:
                                if bitrate_val.lower().endswith('m'):
                                    num = float(bitrate_val[:-1]) * 1000
                                elif bitrate_val.lower().endswith('k'):
                                    num = float(bitrate_val[:-1])
                                else:
                                    num = float(bitrate_val)
                                command_args.extend(['-bufsize', f"{int(num * 2)}k"])
                            except ValueError:
                                command_args.extend(['-bufsize', bitrate_val])
                else:
                    if self.use_gpu:
                        command_args.extend(['-b:v', '5000k', '-maxrate', '5000k', '-bufsize', '10000k'])
                    elif "libx264" in final_v_encoder:
                        command_args.extend(['-crf', '23'])
            elif not self.is_advanced and self.use_gpu:
                bitrate_map = {"High": "6000k", "Medium": "4000k", "Low": "2000k",
                               "Tinggi": "6000k", "Sedang": "4000k", "Rendah": "2000k"}
                val = bitrate_map.get(self.quality) or "4000k"
                command_args.extend(['-b:v', val])
            elif not self.is_advanced and not self.use_gpu:
                quality_map = {"High": "18", "Medium": "23", "Low": "28",
                               "Tinggi": "18", "Sedang": "23", "Rendah": "28"}
                val = quality_map.get(self.quality, "23")
                command_args.extend(['-crf', val])
                command_args.extend(['-preset', 'medium'])

            # B. Advanced: Ref Frames & CABAC
            if self.is_advanced:
                if "libx264" in final_v_encoder:
                    x264_params = []
                    if self.ref_frames > 0:
                        x264_params.append(f"ref={self.ref_frames}")
                    x264_params.append(f"cabac={1 if self.use_cabac else 0}")
                    if x264_params:
                        command_args.extend(['-x264-params', ":".join(x264_params)])
                elif "nvenc" in final_v_encoder:
                    if self.ref_frames > 0:
                        command_args.extend(['-refs', str(self.ref_frames)])
                    if self.use_cabac:
                        command_args.extend(['-coder', 'cabac'])
        else:
            command_args.extend(['-c:v', 'copy'])

        # --- 5. FPS ---
        if self.is_advanced and self.fps != "Original":
            command_args.extend(['-r', self.fps])

        # --- 6. Custom Flags ---
        if self.is_advanced and self.custom_flags.strip():
            command_args.extend(self.custom_flags.strip().split(' '))

        # --- 6b. Subtitle ---
        subtitle_valid = self.subtitle_path and os.path.isfile(self.subtitle_path)
        is_hardsub = self.subtitle_mode in ["Burn-in (Hardcode)"]
        is_softsub = self.subtitle_mode in ["Embed (Softcode, MKV)"]

        if subtitle_valid:
            sub_ext = os.path.splitext(self.subtitle_path)[1].lower()
            if is_hardsub:
                safe_sub_path = self.subtitle_path.replace('\\', '/').replace(':', '\\:')
                if sub_ext == '.ass':
                    sub_filter = f"ass='{safe_sub_path}'"
                else:
                    sub_filter = f"subtitles='{safe_sub_path}'"

                existing_vf = None
                for i, arg in enumerate(command_args):
                    if arg == '-vf' and i + 1 < len(command_args):
                        existing_vf = i + 1
                        break
                if existing_vf is not None:
                    command_args[existing_vf] = command_args[existing_vf] + ',' + sub_filter
                else:
                    command_args.extend(['-vf', sub_filter])
            elif is_softsub and self.out_format in ['mkv', 'mp4']:
                command_args.extend(['-i', self.subtitle_path])
                command_args.extend(['-c:s', 'srt' if self.out_format == 'mp4' else 'copy'])
                command_args.extend(['-map', '0', '-map', '1'])

        # --- 7. Audio Settings ---
        if self.is_advanced:
            if self.a_encoder != "copy":
                command_args.extend(['-c:a', self.a_encoder])
                if self.a_channels != "Original":
                    command_args.extend(['-ac', self.a_channels])
                if self.a_samplerate != "Original":
                    command_args.extend(['-ar', self.a_samplerate])
                if self.a_bitrate != "Original":
                    command_args.extend(['-b:a', self.a_bitrate])
            else:
                command_args.extend(['-c:a', 'copy'])
        else:
            no_audio_formats = ["gif"]
            wmv_audio = ["wmv"]
            ogg_audio = ["ogv"]
            mp3_audio = ["flv"]
            if self.out_format in no_audio_formats:
                pass
            elif self.out_format in wmv_audio:
                command_args.extend(['-c:a', 'wmav2', '-b:a', '192k'])
            elif self.out_format in ogg_audio:
                command_args.extend(['-c:a', 'libvorbis', '-b:a', '192k'])
            elif self.out_format in mp3_audio:
                command_args.extend(['-c:a', 'libmp3lame', '-b:a', '192k'])
            else:
                command_args.extend(['-c:a', 'aac', '-b:a', '192k'])

        # --- 8. Output ---
        command_args.extend(['-y', output_filename])
        print("FFMPEG COMMAND:", " ".join(command_args))

        # --- 9. Eksekusi ---
        try:
            self.progress_updated.emit(0, self.lang.get("getting_video_info", "Getting video info..."))
            self.total_duration = self._get_media_duration()

            self.process = _make_hidden_qprocess()
            self.process.readyReadStandardError.connect(self._read_progress)
            self.process.finished.connect(self._on_process_finished)

            self._conversion_start_time = time.time()
            self.process.start(self.ffmpeg_path, command_args)

            if not self.process.waitForStarted():
                self.conversion_error.emit(self.lang.get("ffmpeg_failed_to_start", "Failed to start ffmpeg."))
                return
        except Exception as e:
            if self.is_running:
                self.conversion_error.emit(str(e))

    def _read_progress(self):
        if not self.process or not self.is_running:
            return
        raw = bytes(self.process.readAllStandardError()).decode('utf-8', 'ignore')
        self._stderr_buffer += raw

        if not self.total_duration:
            return

        last_line = ""
        if '\r' in raw:
            last_line = raw.strip().split('\r')[-1]
        else:
            lines = raw.strip().split('\n')
            if lines: last_line = lines[-1]

        if last_line:
            time_search = self.time_regex.search(last_line)
            if time_search:
                h, m, s = map(int, time_search.groups()[:3])
                current_time = (h * 3600) + (m * 60) + s
                if current_time > self.total_duration:
                    self.total_duration = current_time

                progress = min(int((current_time / self.total_duration) * 100), 100)

                eta_str = ""
                if self._conversion_start_time and progress > 0:
                    elapsed = time.time() - self._conversion_start_time
                    if progress < 100:
                        total_estimated = elapsed / (progress / 100.0)
                        remaining = max(0, int(total_estimated - elapsed))
                        rem_m, rem_s = divmod(remaining, 60)
                        eta_str = " — " + self.lang.get("eta_label", "ETA: {time}").format(time=f"{rem_m:02d}:{rem_s:02d}")

                status_text = self.lang["converting_progress"].format(progress=progress) + eta_str
                self.progress_updated.emit(progress, status_text)

    def _on_process_finished(self, exit_code):
        if not self.is_running:
            self.conversion_error.emit(self.lang.get("conversion_stopped", "Conversion stopped."))
        elif exit_code == 0:
            self.progress_updated.emit(100, self.lang["done"])
            self.conversion_finished.emit(self.lang["video_conversion_success"].format(format=self.out_format.upper()))
        else:
            error_msg = self._stderr_buffer
            if not error_msg.strip():
                error_msg = bytes(self.process.readAllStandardError()).decode('utf-8', 'ignore')

            relevant_lines = [l for l in error_msg.splitlines() if any(
                kw in l.lower() for kw in ['error', 'invalid', 'failed', 'unknown', 'not found', 'cannot', 'no such']
            )]
            short_error = '\n'.join(relevant_lines[-5:]) if relevant_lines else error_msg[-800:]

            gpu_hint = ""
            if self.use_gpu:
                gpu_hint = ("\n\nTips GPU:\n"
                            "- Pastikan driver NVIDIA terbaru sudah terinstal\n"
                            "- Coba FFmpeg versi terbaru yang mendukung NVENC\n"
                            "- Jika tetap gagal, nonaktifkan 'GPU Rendering' dan coba lagi")

            self.conversion_error.emit(
                self.lang["ffmpeg_failed_with_code"].format(code=exit_code, error=short_error) + gpu_hint
            )

    def stop(self):
        self.is_running = False
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()


# =============================================================================
# WORKER — Ekstrak 1 frame terakhir tiap detik (jpg/png)
# Diporting dari macan_converter (VideoFrameExtractWorker)
# =============================================================================
class VideoFrameExtractWorker(QObject):
    progress_updated = Signal(int, str)
    conversion_finished = Signal(str)
    conversion_error = Signal(str)

    def __init__(self, ffmpeg_path, input_path, output_path, img_format, lang_dict=None):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path
        self.input_path = input_path
        self.output_path = output_path
        self.img_format = img_format.lower()
        self.lang = lang_dict if lang_dict else LANGUAGES["id"]
        self.is_running = True

    def stop(self):
        self.is_running = False

    def _get_video_info(self):
        return _probe_duration_fps(self.ffmpeg_path, self.input_path)

    def run(self):
        try:
            self.progress_updated.emit(0, self.lang.get("getting_video_info", "Getting video info..."))
            duration_sec, fps = self._get_video_info()
            if not duration_sec or not fps:
                self.conversion_error.emit("Gagal membaca info video (durasi/fps).")
                return
            if not self.is_running:
                return

            base_name = os.path.splitext(os.path.basename(self.input_path))[0]
            output_folder = os.path.join(self.output_path, f"{base_name}_frames")
            os.makedirs(output_folder, exist_ok=True)

            total_seconds = duration_sec
            extracted_count = 0

            for sec in range(total_seconds):
                if not self.is_running:
                    break
                timestamp = sec + 1.0 - (1.0 / fps)
                timestamp = min(timestamp, duration_sec - (1.0 / fps))
                out_filename = os.path.join(output_folder, f"{base_name}_sec{sec+1:05d}.{self.img_format}")
                cmd_args = ['-ss', f"{timestamp:.6f}", '-i', self.input_path, '-vframes', '1',
                            '-q:v', '2' if self.img_format == 'jpg' else '0', '-y', out_filename]
                process = _make_hidden_qprocess()
                process.start(self.ffmpeg_path, cmd_args)
                process.waitForFinished(30000)
                if process.exitCode() == 0 and os.path.exists(out_filename):
                    extracted_count += 1
                progress = int(((sec + 1) / total_seconds) * 100)
                status = self.lang.get("frame_extract_progress", "Extracting frame {sec}/{total}...").format(sec=sec + 1, total=total_seconds)
                self.progress_updated.emit(progress, status)

            if self.is_running:
                folder_name = os.path.basename(output_folder)
                msg = self.lang.get("frame_extract_success", "Success! {count} frames extracted to '{folder}'.").format(count=extracted_count, folder=folder_name)
                self.conversion_finished.emit(msg)
            else:
                self.conversion_error.emit(self.lang.get("conversion_stopped", "Conversion stopped."))
        except Exception as e:
            if self.is_running:
                self.conversion_error.emit(str(e))


# =============================================================================
# WORKER — Ekstrak SEMUA frame video (jpg/png)
# Diporting dari macan_converter (VideoAllFramesExtractWorker)
# =============================================================================
class VideoAllFramesExtractWorker(QObject):
    progress_updated = Signal(int, str)
    conversion_finished = Signal(str)
    conversion_error = Signal(str)

    def __init__(self, ffmpeg_path, input_path, output_path, img_format, lang_dict=None):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path
        self.input_path = input_path
        self.output_path = output_path
        self.img_format = img_format.lower()
        self.lang = lang_dict if lang_dict else LANGUAGES["id"]
        self.is_running = True
        self.process = None
        self.frame_regex = re.compile(r"frame=\s*(\d+)")
        self._stderr_buffer = ""

    def stop(self):
        self.is_running = False
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()

    def _get_video_info(self):
        duration_sec, fps = _probe_duration_fps(self.ffmpeg_path, self.input_path)
        return (float(duration_sec) if duration_sec is not None else None), fps

    def run(self):
        try:
            self.progress_updated.emit(0, self.lang.get("getting_video_info", "Getting video info..."))
            duration_sec, fps = self._get_video_info()
            if not duration_sec or not fps:
                self.conversion_error.emit("Gagal membaca info video (durasi/fps).")
                return

            base_name = os.path.splitext(os.path.basename(self.input_path))[0]
            output_folder = os.path.join(self.output_path, f"{base_name}_allframes")
            os.makedirs(output_folder, exist_ok=True)

            total_frames_estimate = int(duration_sec * fps)
            out_pattern = os.path.join(output_folder, f"{base_name}_frame%06d.{self.img_format}")
            q_val = '2' if self.img_format == 'jpg' else '1'
            cmd_args = ['-i', self.input_path, '-q:v', q_val, '-y', out_pattern]

            print("FFMPEG ALL FRAMES:", " ".join([self.ffmpeg_path] + cmd_args))

            self._stderr_buffer = ""
            self.process = _make_hidden_qprocess()
            self.process.readyReadStandardError.connect(self._read_progress_all)
            self._total_frames_est = total_frames_estimate
            self._base_name = base_name
            self._output_folder = output_folder

            self.process.start(self.ffmpeg_path, cmd_args)
            if not self.process.waitForStarted():
                self.conversion_error.emit(self.lang.get("ffmpeg_failed_to_start", "Failed to start ffmpeg."))
                return

            self.process.waitForFinished(-1)

            if not self.is_running:
                self.conversion_error.emit(self.lang.get("conversion_stopped", "Conversion stopped."))
                return

            exit_code = self.process.exitCode()
            if exit_code == 0:
                count = len([f for f in os.listdir(output_folder) if f.lower().endswith(f'.{self.img_format}')])
                folder_name = os.path.basename(output_folder)
                msg = self.lang.get("frame_extract_all_success", "Success! {count} frames extracted to '{folder}'.").format(count=count, folder=folder_name)
                self.progress_updated.emit(100, self.lang.get("done", "Done!"))
                self.conversion_finished.emit(msg)
            else:
                err = self._stderr_buffer[-500:]
                self.conversion_error.emit(f"FFmpeg gagal (exit {exit_code}):\n{err}")
        except Exception as e:
            if self.is_running:
                self.conversion_error.emit(str(e))

    def _read_progress_all(self):
        if not self.process:
            return
        raw = bytes(self.process.readAllStandardError()).decode('utf-8', 'ignore')
        self._stderr_buffer += raw
        for line in raw.split('\r'):
            match = self.frame_regex.search(line)
            if match:
                current_frame = int(match.group(1))
                progress = min(int((current_frame / self._total_frames_est) * 100), 99) if self._total_frames_est > 0 else 0
                status = self.lang.get("frame_extract_all_progress", "Extracting frame {current}/~{total}...").format(current=current_frame, total=self._total_frames_est)
                self.progress_updated.emit(progress, status)


# =============================================================================
# WIDGET — Halaman Video Converter (modul untuk Macan Video Downloader)
# =============================================================================
class VideoConverterWidget(QWidget):
    def __init__(self, parent=None, initial_lang="id"):
        super().__init__(parent)
        self.current_lang = initial_lang
        self.lang = LANGUAGES.get(self.current_lang, LANGUAGES["id"])
        self.settings = QSettings("MacanAngkasa", "MacanVideoConverterModule")
        self.worker = None; self.thread = None; self.batch_files = []
        self.current_batch_index = 0
        self.init_ui()
        self._load_settings()
        self.retranslate_ui()

    def init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20); layout.setSpacing(15)

        # 1. INPUT
        f1 = QFrame(); f1.setObjectName("groupFrame")
        l1 = QVBoxLayout(f1)
        h1 = QHBoxLayout()
        self.lbl_input = QLabel(); self.lbl_input.setStyleSheet("font-weight:bold")
        self.chk_batch = QCheckBox()
        self.chk_batch.stateChanged.connect(self.toggle_batch)
        h1.addWidget(self.lbl_input); h1.addStretch(); h1.addWidget(self.chk_batch)
        l1.addLayout(h1)

        h2 = QHBoxLayout()
        self.txt_input = QLineEdit(); self.txt_input.setReadOnly(True)
        self.btn_browse = QPushButton(); self.btn_browse.setIcon(get_icon_from_svg(SVG_ICONS["browse"], "#f0f0f0"))
        self.btn_browse.clicked.connect(self.browse_input)
        h2.addWidget(self.txt_input); h2.addWidget(self.btn_browse)
        l1.addLayout(h2)
        layout.addWidget(f1)

        # 2. OUTPUT
        f2 = QFrame(); f2.setObjectName("groupFrame")
        l2 = QVBoxLayout(f2)
        self.lbl_output = QLabel(); self.lbl_output.setStyleSheet("font-weight:bold")
        l2.addWidget(self.lbl_output)
        h3 = QHBoxLayout()
        self.txt_output = QLineEdit()
        self.btn_out_browse = QPushButton(); self.btn_out_browse.setIcon(get_icon_from_svg(SVG_ICONS["folder"], "#f0f0f0"))
        self.btn_out_browse.clicked.connect(self.browse_output)
        h3.addWidget(self.txt_output); h3.addWidget(self.btn_out_browse)
        l2.addLayout(h3)
        layout.addWidget(f2)

        # 3. OPTIONS (dasar)
        f3 = QFrame(); f3.setObjectName("groupFrame")
        l3 = QVBoxLayout(f3)
        self.lbl_options = QLabel(); self.lbl_options.setStyleSheet("font-weight:bold")
        l3.addWidget(self.lbl_options)

        basic_grid = QGridLayout()
        basic_grid.setColumnStretch(1, 1)
        self.lbl_fmt = QLabel(); self.cmb_fmt = QComboBox()
        self.cmb_fmt.currentTextChanged.connect(self._update_video_encoders)
        basic_grid.addWidget(self.lbl_fmt, 0, 0); basic_grid.addWidget(self.cmb_fmt, 0, 1)

        self.lbl_res = QLabel(); self.cmb_res = QComboBox()
        self.cmb_res.addItems(["Original Size", "360p", "480p", "720p", "1080p", "2K", "4K"])
        basic_grid.addWidget(self.lbl_res, 1, 0); basic_grid.addWidget(self.cmb_res, 1, 1)

        self.lbl_qual = QLabel(); self.cmb_qual = QComboBox()
        basic_grid.addWidget(self.lbl_qual, 2, 0); basic_grid.addWidget(self.cmb_qual, 2, 1)
        l3.addLayout(basic_grid)

        # Mode ekstraksi frame (hanya tampak jika format = jpg/png Frame)
        frame_mode_row = QHBoxLayout()
        self.lbl_frame_mode = QLabel()
        self.cmb_frame_mode = QComboBox()
        frame_mode_row.addWidget(self.lbl_frame_mode); frame_mode_row.addWidget(self.cmb_frame_mode, 1)
        l3.addLayout(frame_mode_row)
        self.lbl_frame_mode.setVisible(False); self.cmb_frame_mode.setVisible(False)

        # Advanced & GPU checkbox
        chk_row = QHBoxLayout()
        self.chk_advanced = QCheckBox()
        self.chk_advanced.toggled.connect(self._toggle_advanced_options)
        self.chk_gpu = QCheckBox()
        self.chk_gpu.setToolTip("Hardware acceleration (NVIDIA NVENC), jika tersedia.")
        chk_row.addWidget(self.chk_advanced); chk_row.addWidget(self.chk_gpu); chk_row.addStretch()
        l3.addLayout(chk_row)
        layout.addWidget(f3)

        # 4. SUBTITLE
        f4 = QFrame(); f4.setObjectName("groupFrame")
        l4 = QVBoxLayout(f4)
        self.lbl_subtitle = QLabel(); self.lbl_subtitle.setStyleSheet("font-weight:bold")
        l4.addWidget(self.lbl_subtitle)
        sub_row = QHBoxLayout()
        self.txt_subtitle = QLineEdit(); self.txt_subtitle.setReadOnly(True)
        self.btn_subtitle = QPushButton(); self.btn_subtitle.clicked.connect(self.browse_subtitle)
        self.btn_subtitle_clear = QPushButton("✕"); self.btn_subtitle_clear.setFixedWidth(28)
        self.btn_subtitle_clear.clicked.connect(lambda: self.txt_subtitle.clear())
        sub_row.addWidget(self.txt_subtitle, 1); sub_row.addWidget(self.btn_subtitle); sub_row.addWidget(self.btn_subtitle_clear)
        l4.addLayout(sub_row)
        sub_mode_row = QHBoxLayout()
        self.lbl_subtitle_mode = QLabel(); self.cmb_subtitle_mode = QComboBox()
        sub_mode_row.addWidget(self.lbl_subtitle_mode); sub_mode_row.addWidget(self.cmb_subtitle_mode, 1)
        l4.addLayout(sub_mode_row)
        layout.addWidget(f4)

        # 5. ADVANCED (disembunyikan secara default)
        self.frame_advanced = QFrame(); self.frame_advanced.setObjectName("groupFrame")
        adv_layout = QVBoxLayout(self.frame_advanced)
        adv_grid = QGridLayout()
        adv_grid.setColumnStretch(1, 1)

        self.lbl_v_bitrate = QLabel(); self.cmb_v_bitrate = QComboBox()
        self.cmb_v_bitrate.setEditable(True)
        self.cmb_v_bitrate.addItems(["Auto", "1000k", "2500k", "5000k", "8000k", "10000k"])
        adv_grid.addWidget(self.lbl_v_bitrate, 0, 0); adv_grid.addWidget(self.cmb_v_bitrate, 0, 1)

        self.lbl_v_encoder = QLabel(); self.cmb_v_encoder = QComboBox()
        adv_grid.addWidget(self.lbl_v_encoder, 1, 0); adv_grid.addWidget(self.cmb_v_encoder, 1, 1)

        self.lbl_fps = QLabel(); self.cmb_fps = QComboBox()
        self.cmb_fps.addItems(["Original", "24", "25", "30", "50", "60"])
        adv_grid.addWidget(self.lbl_fps, 2, 0); adv_grid.addWidget(self.cmb_fps, 2, 1)

        self.lbl_a_encoder = QLabel(); self.cmb_a_encoder = QComboBox()
        self.cmb_a_encoder.addItems(["aac", "libmp3lame (MP3)", "ac3", "copy"])
        adv_grid.addWidget(self.lbl_a_encoder, 3, 0); adv_grid.addWidget(self.cmb_a_encoder, 3, 1)

        self.lbl_a_channels = QLabel(); self.cmb_a_channels = QComboBox()
        self.cmb_a_channels.addItems(["Original", "1 (Mono)", "2 (Stereo)"])
        adv_grid.addWidget(self.lbl_a_channels, 4, 0); adv_grid.addWidget(self.cmb_a_channels, 4, 1)

        self.lbl_a_samplerate = QLabel(); self.cmb_a_samplerate = QComboBox()
        self.cmb_a_samplerate.addItems(["Original", "22050", "44100", "48000"])
        adv_grid.addWidget(self.lbl_a_samplerate, 5, 0); adv_grid.addWidget(self.cmb_a_samplerate, 5, 1)

        self.lbl_a_bitrate = QLabel(); self.cmb_a_bitrate = QComboBox()
        self.cmb_a_bitrate.addItems(["Original", "96k", "128k", "192k", "256k", "320k"])
        adv_grid.addWidget(self.lbl_a_bitrate, 6, 0); adv_grid.addWidget(self.cmb_a_bitrate, 6, 1)

        self.lbl_ref = QLabel(); self.spin_ref = QSpinBox()
        self.spin_ref.setRange(0, 16); self.spin_ref.setValue(0); self.spin_ref.setSpecialValueText("Auto")
        adv_grid.addWidget(self.lbl_ref, 7, 0); adv_grid.addWidget(self.spin_ref, 7, 1)

        self.chk_cabac = QCheckBox(); self.chk_cabac.setChecked(True)
        adv_grid.addWidget(self.chk_cabac, 8, 0, 1, 2)

        self.lbl_custom_flags = QLabel(); self.txt_custom_flags = QLineEdit()
        self.txt_custom_flags.setPlaceholderText("-profile:v high -level 4.1")
        adv_grid.addWidget(self.lbl_custom_flags, 9, 0); adv_grid.addWidget(self.txt_custom_flags, 9, 1)

        adv_layout.addLayout(adv_grid)
        layout.addWidget(self.frame_advanced)
        self.frame_advanced.setVisible(False)

        layout.addStretch()
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

        # ACTION (tetap di luar scroll area)
        action_frame = QWidget()
        action_layout = QVBoxLayout(action_frame)
        action_layout.setContentsMargins(20, 10, 20, 15); action_layout.setSpacing(8)

        h5 = QHBoxLayout()
        self.btn_stop = QPushButton(); self.btn_stop.setIcon(get_icon_from_svg(SVG_ICONS["stop"], "#f0f0f0"))
        self.btn_stop.setEnabled(False); self.btn_stop.clicked.connect(self.stop_conversion)
        self.btn_start = QPushButton(); self.btn_start.setIcon(get_icon_from_svg(SVG_ICONS["play"], "#fff"))
        self.btn_start.setObjectName("startButton"); self.btn_start.clicked.connect(self.start_conversion)
        h5.addStretch(); h5.addWidget(self.btn_stop); h5.addWidget(self.btn_start)
        action_layout.addLayout(h5)

        self.pbar = QProgressBar(); self.pbar.setTextVisible(False); self.pbar.setFixedHeight(5)
        action_layout.addWidget(self.pbar)
        self.lbl_status = QLabel(); self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color: #888; font-style: italic;")
        action_layout.addWidget(self.lbl_status)

        outer_layout.addWidget(action_frame)

    # --- Bahasa ---
    def set_language(self, code):
        self.current_lang = code; self.lang = LANGUAGES.get(code, LANGUAGES["id"])
        self.retranslate_ui()

    def retranslate_ui(self):
        self.lbl_input.setText(self.lang["input_vid_label"])
        self.chk_batch.setText(self.lang["batch_mode_checkbox"])
        self.btn_browse.setText(self.lang["browse_btn"])
        self.lbl_output.setText(self.lang["output_label"])
        self.lbl_options.setText(self.lang["vid_options_label"])
        self.lbl_fmt.setText(self.lang["output_format_label"])
        self.lbl_res.setText(self.lang["resolution_label"])
        self.lbl_qual.setText(self.lang["quality_label"])
        self.lbl_frame_mode.setText(self.lang["frame_extract_mode_label"])
        self.chk_advanced.setText(self.lang["advanced_checkbox"])
        self.chk_gpu.setText(self.lang["gpu_checkbox"])
        self.lbl_subtitle.setText(self.lang["subtitle_label"])
        self.btn_subtitle.setText(self.lang["subtitle_btn"])
        self.txt_subtitle.setPlaceholderText(self.lang["subtitle_no_file"])
        self.lbl_subtitle_mode.setText(self.lang["subtitle_mode_label"])
        self.lbl_v_bitrate.setText(self.lang["video_bitrate_label"])
        self.lbl_v_encoder.setText(self.lang["video_encoder_label"])
        self.lbl_fps.setText(self.lang["fps_label"])
        self.lbl_a_encoder.setText(self.lang["audio_encoder_label"])
        self.lbl_a_channels.setText(self.lang["channels_label"])
        self.lbl_a_samplerate.setText(self.lang["sample_rate_label"])
        self.lbl_a_bitrate.setText(self.lang["audio_bitrate_label"])
        self.lbl_ref.setText(self.lang["ref_frames_label"])
        self.chk_cabac.setText(self.lang["cabac_label"])
        self.lbl_custom_flags.setText(self.lang["custom_flags_label"])
        self.btn_start.setText(self.lang["start_conversion_btn"])
        self.btn_stop.setText(self.lang["stop_conversion_btn"])
        self.lbl_status.setText(self.lang["ready_status"])

        current_fmt = self.cmb_fmt.currentText()
        self.cmb_fmt.blockSignals(True)
        self.cmb_fmt.clear(); self.cmb_fmt.addItems(self.lang["vid_formats"])
        if current_fmt and self.cmb_fmt.findText(current_fmt) >= 0:
            self.cmb_fmt.setCurrentText(current_fmt)
        self.cmb_fmt.blockSignals(False)

        self.cmb_qual.clear(); self.cmb_qual.addItems(self.lang["vid_qualities"])
        self.cmb_qual.setCurrentIndex(1)

        self.cmb_frame_mode.clear()
        self.cmb_frame_mode.addItems([self.lang["frame_extract_mode_per_sec"], self.lang["frame_extract_mode_all"]])

        self.cmb_subtitle_mode.clear()
        self.cmb_subtitle_mode.addItems(self.lang["subtitle_modes"])

        self._update_video_encoders()

    # --- Update daftar encoder video sesuai format container ---
    def _update_video_encoders(self):
        format_ = self.cmb_fmt.currentText().lower()
        self.cmb_v_encoder.clear()

        encoder_map = {
            "mp4": ["libx264 (H.264)", "libx265 (H.265)", "copy"],
            "mkv": ["libx264 (H.264)", "libx265 (H.265)", "vp9 (WebM)", "copy"],
            "webm": ["vp9 (WebM)", "copy"],
            "avi": ["mpeg4 (DivX)", "libx264 (H.264)", "copy"],
            "mov": ["libx264 (H.264)", "libx265 (H.265)", "copy"],
            "ts": ["libx264 (H.264)", "libx265 (H.265)", "mpeg2video (MPEG-2)", "copy"],
            "flv": ["libx264 (H.264)", "flv (Flash)", "copy"],
            "wmv": ["wmv2 (WMV2)", "msmpeg4v3 (WMV3)", "copy"],
            "3gp": ["libx264 (H.264)", "mpeg4 (MPEG-4)", "copy"],
            "m4v": ["libx264 (H.264)", "libx265 (H.265)", "copy"],
            "ogv": ["libtheora (Theora)", "copy"],
            "vob": ["mpeg2video (MPEG-2)", "copy"],
            "divx": ["mpeg4 (DivX)", "libx264 (H.264)", "copy"],
            "f4v": ["libx264 (H.264)", "copy"],
        }

        is_frame_mode = format_ in ["jpg (frame)", "png (frame)"]
        is_gif = format_ == "gif"

        if is_frame_mode:
            self.cmb_v_encoder.addItems(["(Frame Extraction)"])
            self.chk_advanced.setEnabled(False); self.chk_advanced.setChecked(False)
        elif is_gif:
            self.cmb_v_encoder.addItems(["gif"])
            self.chk_advanced.setEnabled(False); self.chk_advanced.setChecked(False)
        else:
            self.cmb_v_encoder.addItems(encoder_map.get(format_, ["libx264 (H.264)", "copy"]))
            self.chk_advanced.setEnabled(True)

        # Tampilkan/sembunyikan kontrol sesuai mode
        self.lbl_qual.setVisible(not is_frame_mode)
        self.cmb_qual.setVisible(not is_frame_mode)
        self.lbl_res.setVisible(not is_frame_mode)
        self.cmb_res.setVisible(not is_frame_mode)
        self.lbl_frame_mode.setVisible(is_frame_mode)
        self.cmb_frame_mode.setVisible(is_frame_mode)
        # Subtitle & advanced tak relevan untuk mode ekstraksi frame
        self.frame_advanced.setEnabled(not is_frame_mode)
        self.txt_subtitle.setEnabled(not is_frame_mode)
        self.btn_subtitle.setEnabled(not is_frame_mode)
        self.cmb_subtitle_mode.setEnabled(not is_frame_mode)

    def _toggle_advanced_options(self, is_checked):
        self.frame_advanced.setVisible(is_checked)
        self.lbl_qual.setVisible(not is_checked)
        self.cmb_qual.setVisible(not is_checked)

    # --- Batch / Browse ---
    def toggle_batch(self):
        self.txt_input.clear(); self.batch_files = []
        self.txt_input.setPlaceholderText("Select multiple files..." if self.chk_batch.isChecked() else "Select single file...")

    def browse_input(self):
        flt = "Video (*.mp4 *.mkv *.avi *.mov *.flv *.wmv *.ts *.3gp *.m4v *.ogv *.vob *.divx *.f4v *.webm)"
        if self.chk_batch.isChecked():
            files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", flt)
            if files: self.batch_files = files; self.txt_input.setText(f"{len(files)} files selected")
        else:
            f, _ = QFileDialog.getOpenFileName(self, "Select File", "", flt)
            if f: self.txt_input.setText(f)

    def browse_output(self):
        d = QFileDialog.getExistingDirectory(self, "Select Folder")
        if d: self.txt_output.setText(d)

    def browse_subtitle(self):
        flt = "Subtitle Files (*.srt *.ass *.ssa);;All Files (*)"
        f, _ = QFileDialog.getOpenFileName(self, self.lang["subtitle_btn"], "", flt)
        if f: self.txt_subtitle.setText(f)

    def _find_ffmpeg(self):
        base = sys._MEIPASS if hasattr(sys, "_MEIPASS") else os.path.dirname(os.path.abspath(__file__))
        local = os.path.join(base, "ffmpeg.exe" if os.name == 'nt' else "ffmpeg")
        if os.path.exists(local): return local
        from shutil import which
        return "ffmpeg" if which("ffmpeg") else None

    def _find_ffprobe(self):
        base = sys._MEIPASS if hasattr(sys, "_MEIPASS") else os.path.dirname(os.path.abspath(__file__))
        local = os.path.join(base, "ffprobe.exe" if os.name == 'nt' else "ffprobe")
        if os.path.exists(local): return local
        from shutil import which
        return "ffprobe" if which("ffprobe") else None

    # --- Konversi ---
    def start_conversion(self):
        ffmpeg = self._find_ffmpeg()
        if not ffmpeg:
            QMessageBox.critical(self, self.lang["ffmpeg_not_found_title"], self.lang["ffmpeg_not_found_msg"])
            return
        out_path = self.txt_output.text()
        if not out_path or not os.path.isdir(out_path):
            QMessageBox.warning(self, self.lang["invalid_input_title"], self.lang["invalid_output_folder_msg"])
            return

        if self.chk_batch.isChecked():
            if not self.batch_files:
                QMessageBox.warning(self, self.lang["invalid_input_title"], self.lang["batch_no_files_msg"])
                return
            self.current_batch_index = 0; self._convert_next_batch(ffmpeg)
        else:
            inp = self.txt_input.text()
            if not inp:
                QMessageBox.warning(self, self.lang["invalid_input_title"], self.lang["batch_no_files_msg"])
                return
            self._start_single_conversion(ffmpeg, inp)

    def _convert_next_batch(self, ffmpeg):
        if self.current_batch_index < len(self.batch_files):
            f = self.batch_files[self.current_batch_index]
            self.lbl_status.setText(self.lang["converting_batch_file"].format(
                current=self.current_batch_index + 1, total=len(self.batch_files), filename=os.path.basename(f)))
            self._start_single_conversion(ffmpeg, f)
        else:
            self._set_running(False)
            QMessageBox.information(self, self.lang["batch_complete_title"],
                                     self.lang["batch_complete_msg"].format(count=len(self.batch_files)))

    def _start_single_conversion(self, ffmpeg, input_path):
        self._set_running(True)
        self.lbl_status.setText(self.lang["preparing_conversion"].format(filename=os.path.basename(input_path)))

        current_format = self.cmb_fmt.currentText().lower()
        out_path = self.txt_output.text()

        # --- Mode ekstraksi frame ---
        if current_format in ["jpg (frame)", "png (frame)"]:
            img_format = "jpg" if "jpg" in current_format else "png"
            extract_mode_text = self.cmb_frame_mode.currentText()
            is_all_frames = extract_mode_text == self.lang["frame_extract_mode_all"]
            if is_all_frames:
                self.worker = VideoAllFramesExtractWorker(ffmpeg, input_path, out_path, img_format, self.lang)
            else:
                self.worker = VideoFrameExtractWorker(ffmpeg, input_path, out_path, img_format, self.lang)
            self._launch_worker()
            return

        # --- Mode konversi video normal ---
        self.worker = VideoConversionWorker(
            ffmpeg, input_path, out_path,
            self.cmb_fmt.currentText(), self.cmb_res.currentText(), self.cmb_qual.currentText(), self.lang,
            is_advanced=self.chk_advanced.isChecked(),
            use_gpu=self.chk_gpu.isChecked(),
            v_bitrate=self.cmb_v_bitrate.currentText(),
            fps=self.cmb_fps.currentText(),
            v_encoder=self.cmb_v_encoder.currentText(),
            a_encoder=self.cmb_a_encoder.currentText(),
            a_channels=self.cmb_a_channels.currentText(),
            a_samplerate=self.cmb_a_samplerate.currentText(),
            a_bitrate=self.cmb_a_bitrate.currentText(),
            custom_flags=self.txt_custom_flags.text(),
            ref_frames=self.spin_ref.value(),
            use_cabac=self.chk_cabac.isChecked(),
            subtitle_path=self.txt_subtitle.text(),
            subtitle_mode=self.cmb_subtitle_mode.currentText()
        )
        self._launch_worker()

    def _launch_worker(self):
        self.thread = QThread(); self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress_updated.connect(lambda v, t: (self.pbar.setValue(v), self.lbl_status.setText(t)))
        self.worker.conversion_finished.connect(self._on_finished)
        self.worker.conversion_error.connect(self._on_error)
        self.thread.start()

    def _on_finished(self, msg):
        self.thread.quit(); self.thread.wait()
        if self.chk_batch.isChecked():
            self.current_batch_index += 1
            self._convert_next_batch(self._find_ffmpeg())
        else:
            self._set_running(False)
            QMessageBox.information(self, self.lang["done"], msg)
            self.pbar.setValue(100); self.lbl_status.setText(self.lang["ready_status"])

    def _on_error(self, msg):
        self.thread.quit(); self.thread.wait(); self._set_running(False)
        QMessageBox.critical(self, self.lang["error_title"], msg)

    def stop_conversion(self):
        if self.worker: self.worker.stop()
        self._set_running(False)
        self.lbl_status.setText(self.lang["conversion_stopped"])

    def _set_running(self, running):
        self.btn_start.setEnabled(not running); self.btn_stop.setEnabled(running)
        self.btn_browse.setEnabled(not running); self.chk_batch.setEnabled(not running)

    # --- Settings ---
    def _save_settings(self):
        self.settings.setValue("vid/outputPath", self.txt_output.text())
        self.settings.setValue("vid/format", self.cmb_fmt.currentText())
        self.settings.setValue("vid/resolution", self.cmb_res.currentText())
        self.settings.setValue("vid/advanced", self.chk_advanced.isChecked())
        self.settings.setValue("vid/gpu", self.chk_gpu.isChecked())

    def _load_settings(self):
        self.txt_output.setText(self.settings.value("vid/outputPath", "", type=str))
        self.cmb_fmt.setCurrentText(self.settings.value("vid/format", "mp4", type=str))
        self.cmb_res.setCurrentText(self.settings.value("vid/resolution", "Original Size", type=str))
        self.chk_advanced.setChecked(self.settings.value("vid/advanced", False, type=bool))
        self.chk_gpu.setChecked(self.settings.value("vid/gpu", False, type=bool))

    def save_and_close(self):
        self._save_settings(); self.stop_conversion()


# =============================================================================
# STANDALONE APP
# Bikin VideoConverterWidget bisa dijalankan sendiri sebagai aplikasi
# terpisah (di luar MacanAngkasa suite), lengkap sama window, ikon, dan
# dark theme minimal biar objectName "groupFrame"/"startButton" tetap
# kepakai stylingnya walau gak nempel ke QSS global aplikasi induk.
# =============================================================================
APP_STYLESHEET = """
QWidget {
    background-color: #1e1f22;
    color: #e0e0e0;
    font-size: 13px;
}
QFrame#groupFrame {
    background-color: #2b2d31;
    border: 1px solid #3a3c40;
    border-radius: 8px;
    padding: 10px;
}
QLineEdit, QComboBox, QSpinBox {
    background-color: #1e1f22;
    border: 1px solid #3a3c40;
    border-radius: 4px;
    padding: 4px 6px;
    color: #e0e0e0;
}
QLineEdit:read-only {
    color: #9a9a9a;
}
QPushButton {
    background-color: #3a3c40;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
}
QPushButton:hover {
    background-color: #46484d;
}
QPushButton:disabled {
    color: #6a6a6a;
}
QPushButton#startButton {
    background-color: #2f7d3c;
    color: white;
    font-weight: bold;
}
QPushButton#startButton:hover {
    background-color: #368a43;
}
QPushButton#startButton:disabled {
    background-color: #2b2d31;
    color: #6a6a6a;
}
QProgressBar {
    background-color: #1e1f22;
    border: none;
    border-radius: 2px;
}
QProgressBar::chunk {
    background-color: #2f7d3c;
    border-radius: 2px;
}
QCheckBox {
    spacing: 6px;
}
QScrollArea {
    border: none;
}
"""


class MacanVideoConverterWindow(QWidget):
    """Jendela utama untuk mode standalone."""

    def __init__(self, initial_lang="id", initial_file=None):
        super().__init__()
        self.setWindowTitle("Macan Video Converter")
        self.resize(560, 720)
        self.setWindowIcon(self._load_app_icon())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.converter = VideoConverterWidget(self, initial_lang=initial_lang)
        layout.addWidget(self.converter)

        # Kalau dibuka dengan file (mis. dari menu "Video Converter" di
        # Macan Player Classic, yg ngirim path file yg lagi diputar sbg
        # argumen), langsung isi field input & default output folder-nya.
        if initial_file and os.path.isfile(initial_file):
            self.converter.txt_input.setText(initial_file)
            if not self.converter.txt_output.text():
                self.converter.txt_output.setText(os.path.dirname(initial_file))

    def _load_app_icon(self):
        """Pakai macan_video_converter.ico dari folder aplikasi (root project
        pas dev, atau folder hasil bundle PyInstaller pas udah jadi exe).
        Fallback ke ikon SVG bawaan kalau file .ico gak ketemu."""
        base = sys._MEIPASS if hasattr(sys, "_MEIPASS") else os.path.dirname(os.path.abspath(__file__))
        ico_path = os.path.join(base, "macan_video_converter.ico")
        if os.path.exists(ico_path):
            icon = QIcon(ico_path)
            if not icon.isNull():
                return icon
        return get_icon_from_svg(SVG_ICONS["video"], "#e0e0e0")

    def closeEvent(self, event):
        self.converter.save_and_close()
        super().closeEvent(event)


def _parse_args(argv):
    """Ambil path file dari argumen CLI (dukung juga --file=... dan file
    yg dikirim dgn spasi tanpa quote di beberapa cara pemanggilan)."""
    file_arg = None
    for arg in argv[1:]:
        if arg.startswith('--file='):
            file_arg = arg.split('=', 1)[1]
        elif not arg.startswith('-'):
            file_arg = arg
    return file_arg


def main():
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    app.setApplicationName("MacanVideoConverter")
    app.setOrganizationName("MacanAngkasa")
    app.setStyleSheet(APP_STYLESHEET)

    # Bahasa awal ikut locale sistem: default "id", fallback "en" kalau
    # bukan Indonesia.
    initial_lang = "id"
    try:
        from PySide6.QtCore import QLocale
        if QLocale.system().name().split('_')[0] != 'id':
            initial_lang = "en"
    except Exception:
        pass

    initial_file = _parse_args(sys.argv)

    window = MacanVideoConverterWindow(initial_lang=initial_lang, initial_file=initial_file)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
