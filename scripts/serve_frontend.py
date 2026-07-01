from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the built DataPilot frontend.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5190)
    args = parser.parse_args()

    dist_dir = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    if not (dist_dir / "index.html").exists():
        raise FileNotFoundError("frontend/dist is missing. Run 'npm run build' in frontend first.")

    handler = partial(SimpleHTTPRequestHandler, directory=str(dist_dir))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"DataPilot frontend: http://{args.host}:{args.port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
