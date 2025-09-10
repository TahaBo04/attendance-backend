"""
Usage (local):
  1) Put images in faces/<studentid_fullname>/...jpg
  2) Set BACKEND_URL and SECRET.
  3) python enroll_from_images.py
"""

import os, glob, pickle, requests, numpy as np, face_recognition

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
SECRET = os.getenv("SECRET_TOKEN", "")  # same as backend

FACES_DIR = "faces"

def encode_student_images(folder):
    encs = []
    for imgp in glob.glob(os.path.join(folder, "*")):
        try:
            img = face_recognition.load_image_file(imgp)
            locs = face_recognition.face_locations(img, model="hog")
            encs.extend(face_recognition.face_encodings(img, locs))
        except Exception:
            pass
    return [e.tolist() for e in encs]

def main():
    for person in os.listdir(FACES_DIR):
        path = os.path.join(FACES_DIR, person)
        if not os.path.isdir(path): continue
        # folder name format: <studentid>_<Full Name with underscores>
        sid = person.split("_")[0]
        full_name = " ".join(person.split("_")[1:]) or sid
        encs = encode_student_images(path)
        if not encs:
            print(f"[skip] no faces for {person}")
            continue
        r = requests.post(f"{BACKEND_URL}/enroll",
                          json={"student_id": sid, "full_name": full_name, "encodings": encs},
                          headers={"Authorization": f"Bearer {SECRET}"} if SECRET else {})
        print(person, r.status_code, r.text)

if __name__ == "__main__":
    main()
