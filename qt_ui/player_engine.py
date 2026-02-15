import threading

import numpy as np
import sounddevice as sd
import soundfile as sf


class PlayerEngine:
    """Thread-safe multi-stem audio playback engine with dual timeline modes."""

    def __init__(self):
        self.stream = None
        self.sample_rate = None
        self.stems = []  # list of numpy arrays (N, 2), float32
        self.volumes = []  # per-stem volume multipliers
        self.muted = []  # per-stem mute flags

        self.master_mode = True
        self.master_position = 0
        self.master_playing = False

        self.track_positions = []
        self.track_playing = []
        self.track_lengths = []
        self.master_length = 0

        self.lock = threading.Lock()

    def _stop_stream_locked(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def _ensure_stream_started_locked(self):
        if not self.stems or self.sample_rate is None:
            return

        if self.stream is None:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=2,
                dtype="float32",
                callback=self._callback,
            )
            self.stream.start()
            return

        if not self.stream.active:
            try:
                self.stream.start()
            except Exception:
                # Recreate stream if restarting fails.
                self._stop_stream_locked()
                self.stream = sd.OutputStream(
                    samplerate=self.sample_rate,
                    channels=2,
                    dtype="float32",
                    callback=self._callback,
                )
                self.stream.start()

    def load_files(self, file_paths: list[str]):
        """
        Load stem files and normalize for playback.

        - Clears previous playback state.
        - Reads files with soundfile.
        - Converts audio to float32 stereo.
        - Keeps each stem at original length.
        """
        self.stop()

        loaded_stems = []
        loaded_sr = None

        for path in file_paths:
            data, sr = sf.read(path, always_2d=False)

            if loaded_sr is None:
                loaded_sr = sr
            elif sr != loaded_sr:
                raise ValueError(f"Sample rate mismatch: expected {loaded_sr}, got {sr} for {path}")

            data = np.asarray(data, dtype=np.float32)

            # Convert mono to stereo by duplicating channel.
            if data.ndim == 1:
                data = np.column_stack((data, data))
            elif data.ndim == 2 and data.shape[1] == 1:
                data = np.repeat(data, 2, axis=1)
            elif data.ndim == 2 and data.shape[1] > 2:
                # Keep first two channels for stereo output.
                data = data[:, :2]
            elif data.ndim != 2:
                raise ValueError(f"Unsupported audio shape for {path}: {data.shape}")

            loaded_stems.append(data)

        if not loaded_stems:
            with self.lock:
                self.stream = None
                self.sample_rate = None
                self.stems = []
                self.volumes = []
                self.muted = []
                self.track_positions = []
                self.track_playing = []
                self.track_lengths = []
                self.master_length = 0
                self.master_position = 0
                self.master_playing = False
            return

        track_lengths = [stem.shape[0] for stem in loaded_stems]
        master_length = max(track_lengths)

        with self.lock:
            self._stop_stream_locked()
            self.sample_rate = loaded_sr
            self.stems = loaded_stems
            self.volumes = [1.0 for _ in self.stems]
            self.muted = [False for _ in self.stems]
            self.track_positions = [0 for _ in self.stems]
            self.track_playing = [False for _ in self.stems]
            self.track_lengths = track_lengths
            self.master_length = master_length
            self.master_position = 0
            self.master_playing = False

    def _callback(self, outdata, frames, time, status):
        """
        Mix active stems into output buffer for current playback mode.

        Audio mixing logic:
        - Master mode: all active tracks share one timeline (master_position).
        - Independent mode: each track has its own timeline (track_positions[i]).
        - Each active, unmuted track contributes `stem_slice * volume`.
        - Final mixed buffer is clipped to [-1, 1].
        """
        if status:
            pass

        with self.lock:
            if not self.stems:
                mix = np.zeros((frames, 2), dtype=np.float32)
                outdata[:] = mix
                self.master_playing = False
                for i in range(len(self.track_playing)):
                    self.track_playing[i] = False
                self._stop_stream_locked()
                return

            total_len = self.master_length
            mix = np.zeros((frames, 2), dtype=np.float32)
            should_stop = False

            if self.master_mode:
                if not self.master_playing:
                    should_stop = True

                start = self.master_position
                if not should_stop:
                    for i, stem in enumerate(self.stems):
                        if not self.track_playing[i] or self.muted[i]:
                            continue
                        if start >= self.track_lengths[i]:
                            self.track_playing[i] = False
                            continue
                        end = min(start + frames, self.track_lengths[i])
                        actual_frames = max(0, end - start)
                        if actual_frames > 0:
                            mix[:actual_frames] += stem[start:end] * float(self.volumes[i])

                    self.master_position = min(start + frames, total_len)
                    if self.master_position >= total_len:
                        self.master_playing = False
                        should_stop = True
            else:
                any_track_active = False

                for i, stem in enumerate(self.stems):
                    if not self.track_playing[i]:
                        continue

                    any_track_active = True
                    start = self.track_positions[i]
                    if start >= self.track_lengths[i]:
                        self.track_playing[i] = False
                        continue

                    end = min(start + frames, self.track_lengths[i])
                    actual_frames = max(0, end - start)

                    if actual_frames > 0 and not self.muted[i]:
                        mix[:actual_frames] += stem[start:end] * float(self.volumes[i])

                    self.track_positions[i] = end
                    if end >= total_len:
                        self.track_playing[i] = False

                if not any_track_active or not any(self.track_playing):
                    should_stop = True

            np.clip(mix, -1.0, 1.0, out=mix)
            outdata[:] = mix

            if should_stop:
                self.master_playing = False
                for i in range(len(self.track_playing)):
                    self.track_playing[i] = False
                self._stop_stream_locked()
                return

    def set_master_mode(self, enabled: bool):
        with self.lock:
            self.master_mode = bool(enabled)
            if enabled:
                for i in range(len(self.track_positions)):
                    self.track_positions[i] = min(self.master_position, self.track_lengths[i])

    def play_master(self):
        with self.lock:
            if not self.stems:
                return
            self.master_mode = True
            total_len = self.master_length
            if self.master_position >= total_len:
                self.master_position = 0
            self.master_playing = True
            for i in range(len(self.track_playing)):
                self.track_positions[i] = min(self.master_position, self.track_lengths[i])
                self.track_playing[i] = self.track_positions[i] < self.track_lengths[i]
            self._ensure_stream_started_locked()

    def pause_master(self):
        with self.lock:
            self.master_playing = False
            for i in range(len(self.track_playing)):
                self.track_playing[i] = False
            self._stop_stream_locked()

    def stop_master(self):
        with self.lock:
            self.master_playing = False
            self.master_position = 0
            for i in range(len(self.track_playing)):
                self.track_playing[i] = False
                self.track_positions[i] = 0
            self._stop_stream_locked()

    def play_track(self, index):
        with self.lock:
            if not (0 <= index < len(self.stems)):
                return
            self.master_mode = False
            total_len = self.track_lengths[index]
            if self.track_positions[index] >= total_len:
                self.track_positions[index] = 0
            self.track_playing[index] = True
            self._ensure_stream_started_locked()

    def pause_track(self, index):
        with self.lock:
            if not (0 <= index < len(self.track_playing)):
                return
            self.track_playing[index] = False
            if not any(self.track_playing) and not self.master_playing:
                self._stop_stream_locked()

    def stop_track(self, index):
        with self.lock:
            if not (0 <= index < len(self.track_playing)):
                return
            self.track_playing[index] = False
            self.track_positions[index] = 0
            if not any(self.track_playing) and not self.master_playing:
                self._stop_stream_locked()

    def play(self):
        """Backward-compatible global play control."""
        if self.master_mode:
            self.play_master()
            return
        with self.lock:
            if not self.stems:
                return
            for i in range(len(self.track_playing)):
                if self.track_positions[i] < self.track_lengths[i]:
                    self.track_playing[i] = True
            self._ensure_stream_started_locked()

    def pause(self):
        """Backward-compatible global pause control."""
        if self.master_mode:
            self.pause_master()
            return
        with self.lock:
            for i in range(len(self.track_playing)):
                self.track_playing[i] = False
            self._stop_stream_locked()

    def stop(self):
        """Backward-compatible global stop control."""
        with self.lock:
            self.master_playing = False
            self.master_position = 0
            for i in range(len(self.track_positions)):
                self.track_positions[i] = 0
            for i in range(len(self.track_playing)):
                self.track_playing[i] = False
            self._stop_stream_locked()

    def get_duration(self):
        with self.lock:
            if self.sample_rate is None or self.master_length <= 0:
                return 0.0
            return self.master_length / float(self.sample_rate)

    def get_master_position(self):
        with self.lock:
            if self.sample_rate is None:
                return 0.0
            return self.master_position / float(self.sample_rate)

    def get_track_position(self, index):
        with self.lock:
            if self.sample_rate is None or not (0 <= index < len(self.track_positions)):
                return 0.0
            return self.track_positions[index] / float(self.sample_rate)

    def seek_master(self, seconds):
        with self.lock:
            if self.sample_rate is None:
                return

            frame = int(max(0.0, float(seconds)) * float(self.sample_rate))
            frame = max(0, min(frame, self.master_length))
            self.master_position = frame

            # Sync all track positions to master
            for i in range(len(self.track_positions)):
                self.track_positions[i] = min(frame, self.track_lengths[i])

            # Reactivate tracks that still have audio remaining
            for i in range(len(self.track_playing)):
                if self.track_positions[i] < self.track_lengths[i]:
                    self.track_playing[i] = True

    def seek_track(self, index, seconds):
        with self.lock:
            if self.sample_rate is None or not (0 <= index < len(self.track_positions)):
                return
            frame = int(max(0.0, float(seconds)) * float(self.sample_rate))
            frame = max(0, min(frame, self.track_lengths[index]))
            self.track_positions[index] = frame

    def set_volume(self, index, value):
        """Set per-stem volume multiplier safely."""
        with self.lock:
            if 0 <= index < len(self.volumes):
                self.volumes[index] = float(value)

    def toggle_mute(self, index):
        """Toggle per-stem mute safely."""
        with self.lock:
            if 0 <= index < len(self.muted):
                self.muted[index] = not self.muted[index]
