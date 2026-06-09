import os
filepath = r"d:\JOB\DEV\EveryThingDownloader\downloads\temp_74776160-9c4f-4143-afa8-0f0e25866906\media.mp4"
if os.path.exists(filepath):
    print("File size:", os.path.getsize(filepath))
    with open(filepath, "rb") as f:
        header = f.read(200)
        print("Header:", header)
        print("Is HTML?", b"<html" in header or b"<!DOCTYPE" in header or b"<HTML" in header)
else:
    print("File not found")
