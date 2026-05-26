import os
import pickle
import warnings
import numpy as np
import pandas as pd
import librosa
import sounddevice as sd
import soundfile as sf
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

try:
    import acoustid
    HAS_ACOUSTID = True
except Exception:
    HAS_ACOUSTID = False

warnings.filterwarnings("ignore")


class AudioSearch:
    SAMPLE_RATE    = 22050
    WINDOW_SEC     = 5.0
    HOP_SEC        = 2.5
    N_MFCC         = 20
    HOP_LENGTH     = 512
    CACHE_FILE     = "features_cache_windows.pkl"
    SCALER_FILE    = "scaler_cache.pkl"
    FINGERPRINT_FILE = "fingerprint_cache.pkl"
    AUDIO_FOLDER   = "audio"   # carpeta base donde están los .flac

    def __init__(self, csv_path: str):
        self.csv_path          = csv_path
        self.df                = pd.read_csv(csv_path)
        self.song_windows      = {}
        self.song_window_means = {}
        self.valid_indices     = []
        self.scaler            = None
        self.fingerprints      = {}

    def _resolve_path(self, path_str: str) -> str:
        """Intenta resolver la ruta tal cual; si no existe, busca en audio/<basename>."""
        if not isinstance(path_str, str) or path_str.strip() == "":
            return ""
        p = os.path.expanduser(path_str)
        if os.path.isabs(p) and os.path.exists(p):
            return p
        # relativo al cwd
        p_rel = os.path.join(os.getcwd(), p)
        if os.path.exists(p_rel):
            return os.path.abspath(p_rel)
        # buscar en carpeta audio/
        candidate = os.path.join(os.getcwd(), self.AUDIO_FOLDER, os.path.basename(p))
        if os.path.exists(candidate):
            return os.path.abspath(candidate)
        # fallback: devolver original (no existe)
        return p

    def _preprocess_audio_array(self, y):
        y, _ = librosa.effects.trim(y, top_db=20)
        if y.size == 0:
            return y
        return librosa.util.normalize(y)

    def _extract_features_from_array(self, y, sr):
        mfcc       = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=self.N_MFCC, hop_length=self.HOP_LENGTH)
        mfcc_delta = librosa.feature.delta(mfcc)
        mfcc_pool  = np.concatenate([
            np.mean(mfcc, axis=1), np.std(mfcc, axis=1), np.median(mfcc, axis=1),
            np.mean(mfcc_delta, axis=1), np.std(mfcc_delta, axis=1)
        ])
        chroma      = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=self.HOP_LENGTH)
        chroma_pool = np.concatenate([
            np.mean(chroma, axis=1), np.std(chroma, axis=1), np.median(chroma, axis=1)
        ])
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=self.HOP_LENGTH)
        zcr      = librosa.feature.zero_crossing_rate(y, hop_length=self.HOP_LENGTH)
        return np.concatenate([
            mfcc_pool, chroma_pool,
            [np.mean(centroid), np.std(centroid), np.mean(zcr), np.std(zcr)]
        ])

    def _extract_windows_features(self, audio_path):
        try:
            y, sr = librosa.load(audio_path, sr=self.SAMPLE_RATE, mono=True)
            if y is None or y.size == 0:
                return np.empty((0,)), 0
            y = self._preprocess_audio_array(y)
            if y.size == 0:
                return np.empty((0,)), 0
            win, hop = int(self.WINDOW_SEC * sr), int(self.HOP_SEC * sr)
            feats = []
            for start in range(0, max(1, len(y) - win + 1), hop):
                seg = y[start:start + win]
                if seg.size < 256:
                    continue
                feats.append(self._extract_features_from_array(seg, sr))
            if not feats:
                return np.array([self._extract_features_from_array(y, sr)]), sr
            return np.array(feats), sr
        except Exception as e:
            print(f"   ⚠️ Error procesando {audio_path} — {e}")
            return np.empty((0,)), 0

    def _fingerprint_file(self, path):
        if not HAS_ACOUSTID:
            return None
        try:
            _, fp = acoustid.fingerprint_file(path)
            return fp
        except Exception:
            return None

    def build_index(self, force_rebuild: bool = False):
        """Construye el índice. Intenta resolver rutas usando audio/ si es necesario."""
        if not force_rebuild and os.path.exists(self.CACHE_FILE) and os.path.exists(self.SCALER_FILE):
            with open(self.CACHE_FILE, "rb") as f:
                cache = pickle.load(f)
            with open(self.SCALER_FILE, "rb") as f:
                self.scaler = pickle.load(f)
            self.song_windows      = cache["song_windows"]
            self.song_window_means = cache["song_window_means"]
            self.valid_indices     = cache["valid_indices"]
            self.fingerprints      = cache.get("fingerprints", {})
            return

        all_windows, song_windows, song_means = [], {}, {}
        valid_indices, fingerprints = [], {}

        for idx, row in self.df.iterrows():
            raw_path = row.get("Audio_Path", "")
            path = self._resolve_path(raw_path)
            if not path or not os.path.exists(path):
                # no existe, saltar
                continue
            feats, sr = self._extract_windows_features(path)
            if feats.size == 0:
                continue
            song_windows[idx] = feats
            song_means[idx]   = np.mean(feats, axis=0)
            valid_indices.append(idx)
            all_windows.append(feats)
            fp = self._fingerprint_file(path)
            if fp:
                fingerprints[idx] = fp

        if not all_windows:
            # no indexó nada
            return

        X        = np.vstack(all_windows)
        scaler   = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        song_windows_scaled, pos = {}, 0
        for idx in valid_indices:
            n = song_windows[idx].shape[0]
            song_windows_scaled[idx] = X_scaled[pos:pos + n]
            pos += n

        self.song_windows      = song_windows_scaled
        self.song_window_means = {i: np.mean(w, axis=0) for i, w in song_windows_scaled.items()}
        self.valid_indices     = valid_indices
        self.scaler            = scaler
        self.fingerprints      = fingerprints

        with open(self.CACHE_FILE, "wb") as f:
            pickle.dump({"song_windows": self.song_windows,
                         "song_window_means": self.song_window_means,
                         "valid_indices": self.valid_indices,
                         "fingerprints": self.fingerprints}, f)
        with open(self.SCALER_FILE, "wb") as f:
            pickle.dump(self.scaler, f)

    def _search_by_windows(self, query_windows, top_n=5):
        if self.scaler is None:
            raise RuntimeError("Ejecuta build_index() primero.")
        q_scaled    = self.scaler.transform(query_windows)
        song_scores = []
        for idx in self.valid_indices:
            windows = self.song_windows.get(idx)
            if windows is None or windows.size == 0:
                continue
            song_scores.append((idx, np.max(cosine_similarity(q_scaled, windows))))
        song_scores.sort(key=lambda x: x[1], reverse=True)
        rows = []
        for rank, (idx, score) in enumerate(song_scores[:top_n], 1):
            r = self.df.iloc[idx]
            rows.append({"Posición": rank, "Título": r.get("Titulo",""),
                         "Artista": r.get("Artista",""), "Álbum": r.get("Album",""),
                         "Género": r.get("Genero",""), "Año": r.get("Año",""),
                         "Similitud": f"{score:.4f}"})
        return pd.DataFrame(rows)

    def _search(self, query_path, top_n=5):
        if HAS_ACOUSTID:
            qfp = self._fingerprint_file(query_path)
            if qfp:
                for idx, fp in self.fingerprints.items():
                    if fp and (qfp == fp or qfp in fp or fp in qfp):
                        r = self.df.iloc[idx]
                        return pd.DataFrame([{"Posición": 1, "Título": r.get("Titulo",""),
                            "Artista": r.get("Artista",""), "Álbum": r.get("Album",""),
                            "Género": r.get("Genero",""), "Año": r.get("Año",""),
                            "Similitud": "1.0000 (fingerprint)"}])
        q_windows, _ = self._extract_windows_features(query_path)
        if q_windows.size == 0:
            return pd.DataFrame()
        return self._search_by_windows(q_windows, top_n=top_n)

    def search_by_file(self, audio_path: str, top_n: int = 5) -> pd.DataFrame:
        return self._search(audio_path, top_n=top_n)

    def search_by_bytes(self, audio_bytes: bytes, filename: str = "upload.wav",
                        top_n: int = 5) -> pd.DataFrame:
        ext  = os.path.splitext(filename)[1] or ".wav"
        tmp  = f"_temp_upload{ext}"
        with open(tmp, "wb") as f:
            f.write(audio_bytes)
        res = self.search_by_file(tmp, top_n=top_n)
        if os.path.exists(tmp):
            os.remove(tmp)
        return res
