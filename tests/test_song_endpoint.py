from fastapi.testclient import TestClient

from app.main import app


def main():
    client = TestClient(app)
    res = client.get("/api/v1/songs/HaU84TfH9nU?limit=50")
    assert res.status_code == 200, f"Status: {res.status_code}, error: {res.text}"
    body = res.json()

    print("Status:", res.status_code)
    print("Top level keys:", list(body.keys()))
    print("Data keys:", list(body["data"].keys()))
    print("ID:", body["data"]["id"])
    print("Name:", body["data"]["name"])
    print("Existing URL:", body["data"]["url"])
    print("Suggested songs count:", len(body["data"]["suggested_songs"]))
    assert body["data"]["id"] == "HaU84TfH9nU"
    assert body["data"]["url"] == "https://music.youtube.com/watch?v=HaU84TfH9nU"
    assert "mp3" not in body, "mp3 should not be in response root"
    assert "mp3" not in body["data"], "mp3 should not be in song data"
    print("All live endpoint assertions verified successfully!")

if __name__ == "__main__":
    main()
