#!/usr/bin/env python3
"""
TheVoid-Helper: Spotify Basic Pitch Audio-to-MIDI Bridge
Converts polyphonic audio (MP3, WAV, FLAC, M4A) to high-precision clean MIDI.
Official Spotify Research: https://github.com/spotify/basic-pitch
Online Web Converter: https://basicpitch.spotify.com/
"""

import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Sử dụng: python3 audio_to_midi_spotify.py <duong_dan_file_audio> [thu_muc_xuat]")
        print("\nĐể chuyển đổi trực tuyến miễn phí bằng AI của Spotify:")
        print("Truy cập: https://basicpitch.spotify.com/")
        sys.exit(1)

    audio_path = sys.argv[1]
    if not os.path.exists(audio_path):
        print(f"Lỗi: Không tìm thấy tệp {audio_path}")
        sys.exit(1)

    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(audio_path) or "."

    try:
        from basic_pitch.inference import predict_and_save
        print(f"Đang sử dụng Spotify Basic Pitch AI để xử lý: {audio_path}...")
        predict_and_save(
            [audio_path],
            output_directory=out_dir,
            save_midi=True,
            sonify_midi=False,
            save_model_outputs=False,
            save_notes=False,
        )
        base = os.path.splitext(os.path.basename(audio_path))[0]
        midi_path = os.path.join(out_dir, f"{base}_basic_pitch.mid")
        print(f"Thành công! Đã xuất tệp MIDI tại: {midi_path}")
    except ImportError:
        print("Chưa cài đặt thư viện basic-pitch trên môi trường Python.")
        print("Cài đặt nhanh bằng lệnh: pip install basic-pitch")
        print("\nHoặc sử dụng ngay Web AI trực tuyến của Spotify:")
        print("-> https://basicpitch.spotify.com/ (Kéo thả file MP3/WAV và tải ngay .mid)")

if __name__ == "__main__":
    main()
