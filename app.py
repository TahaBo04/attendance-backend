import io, base64, os, datetime, pickle
from typing import List, Dict, Any
import numpy as np
from PIL import Image
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import face_recognition

from db import db_init, db_conn, get_students, upsert_student, mark_attendance, recent_attendance, list_today
from security import require_token

# ====== Config ======
CAMERA_ID = os.getenv("CAMERA_ID", "EMI_GATE_WEB")
THRESH = float(os.getenv("THRESH", "0.5"))          # 0.45–0.60 typical
COOLDOWN_MIN = int(os.getenv("COOLDOWN_MIN", "10")) # anti-dup window (minutes)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# ====== App ======
app = FastAPI(title="Attendance Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# init DB
db_init()

# cache students in memory; refreshable
def load_cached_students() -> List[Dict[str, Any]]:
    rows = get_students()
    # rows: [{student_id, full_name, face_enc(bytes)}]
    out = []
    for r in rows:
        enc = pickle.loads(r["face_enc"])  # np.ndarray (128,)
        out.append({"student_id": r["student_id"], "full_name": r["full_name"], "enc": enc})
    return out

STUDENTS = load_cached_students()

class ImageIn(BaseModel):
    image: str  # data URL "data:image/jpeg;base64,...."

@app.post("/recognize")
def recognize(payload: ImageIn, authorization: str = Header(None)):
    require_token(authorization)  # raises if invalid

    # decode
    try:
        _, b64 = payload.image.split(",", 1)
        img = np.array(Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image payload")

    locs = face_recognition.face_locations(img, model="hog")
    encs = face_recognition.face_encodings(img, locs)

    global STUDENTS
    if not STUDENTS:
        STUDENTS = load_cached_students()

    detections = []
    marked_any = False

    for enc, (top, right, bottom, left) in zip(encs, locs):
        if not STUDENTS:
            detections.append({"matched": False, "name": "Unknown", "confidence": 0.0,
                               "box": {"left": left, "top": top, "right": right, "bottom": bottom}})
            continue

        # nearest neighbor (L2)
        dists = [np.linalg.norm(enc - s["enc"]) for s in STUDENTS]
        j = int(np.argmin(dists))
        best = float(dists[j])
        matched = best < THRESH
        sid = STUDENTS[j]["student_id"]
        name = STUDENTS[j]["full_name"]
        conf = max(0.0, 1.0 - best / THRESH) if matched else 0.0

        # cooldown check
        if matched and not recent_attendance(sid, COOLDOWN_MIN):
            ts = datetime.datetime.utcnow().isoformat()
            mark_attendance(sid, ts, CAMERA_ID, "Present")
            marked_any = True

        detections.append({
            "matched": matched,
            "name": name if matched else "Unknown",
            "confidence": conf,
            "box": {"left": left, "top": top, "right": right, "bottom": bottom}
        })

    return {"detections": detections, "marked": marked_any}

# ---- Admin/utility endpoints ----

class EnrollIn(BaseModel):
    student_id: str
    full_name: str
    encodings: List[List[float]]  # allow multiple 128-d vectors; we'll average them

@app.post("/enroll")
def enroll_student(p: EnrollIn, authorization: str = Header(None)):
    require_token(authorization)

    if not p.encodings:
        raise HTTPException(400, "No encodings provided")
    arrs = [np.array(e, dtype=np.float64) for e in p.encodings]
    mean_enc = np.mean(arrs, axis=0)
    if mean_enc.shape != (128,):
        raise HTTPException(400, "Encoding must be 128-d")

    enc_bytes = pickle.dumps(mean_enc)
    upsert_student(p.student_id, p.full_name, enc_bytes)
    # refresh cache
    global STUDENTS
    STUDENTS = load_cached_students()
    return {"ok": True, "student_id": p.student_id}

@app.get("/today")
def today(authorization: str = Header(None)):
    require_token(authorization)
    return {"items": list_today()}

@app.get("/healthz")
def healthz():
    return {"ok": True}
