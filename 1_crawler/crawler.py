import argparse
import certifi
import os
import sys
import ssl
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0 Safari/537.36 "
    "IlibCrawler/1.0 (education)"
)


@dataclass
class FetchResult:
    src_url: str
    status: int
    content_type: str
    data: bytes
    error: Optional[str] = None


def read_urls(path: str) -> List[str]:
    urls: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            u = line.strip()
            if not u:
                continue
            urls.append(u)
    return urls


def http_get(url: str, timeout: int, user_agent: str) -> FetchResult:
    req = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru,en;q=0.6",
            "Connection": "close",
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=timeout, context=ssl.create_default_context(cafile=certifi.where())) as resp:
            status = int(getattr(resp, "status", 200))
            ctype = (resp.headers.get("Content-Type") or "").lower()
            data = resp.read()
            return FetchResult(
                src_url=url,
                status=status,
                content_type=ctype,
                data=data,
                error=None,
            )
    except Exception as e:
        return FetchResult(
            src_url=url,
            status=0,
            content_type="",
            data=b"",
            error=str(e),
        )


def crawl(urls: List[str], out_dir: str, need: int, workers: int, delay: float, timeout: int, user_agent: str) -> None:
    # Проверка существования/создания выходных директорий
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, 'pages'), exist_ok=True)

    # Маппинг троттлинга по хосту
    host_last_ts: Dict[str, float] = {}

    def fetch_throttled(u: str) -> FetchResult:
        """
        Метод для запроса страниц
        """
        # Получаем хост для страницы
        host = urlparse(u).netloc
        now = time.time()
        # Получаем последнее время запроса на хост
        last = host_last_ts.get(host, 0.0)
        # Вычисляем время ожидания
        wait = (last + delay) - now
        if wait > 0:
            time.sleep(wait)

        # Обновляем последнее время запроса на хост
        host_last_ts[host] = time.time()
        return http_get(u, timeout=timeout, user_agent=user_agent)

    saved: List[Tuple[int, str]] = []  # список успешно сохраненных страниц
    skipped: List[str] = []  # список страниц которые не удалось сохранить (ошибка и страниц)
    file_no = 0

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(fetch_throttled, u): u for u in urls}

        for fut in as_completed(futures):
            if len(saved) >= need:
                continue

            src = futures[fut]
            res = fut.result()

            if res.error:
                skipped.append(f"ERR\t{src}\t{res.error}")
                continue

            if not (200 <= res.status < 300):
                skipped.append(f"HTTP{res.status}\t{src}")
                continue

            if "text/html" not in res.content_type:
                skipped.append(f"CTYPE\t{src}\t{res.content_type}")
                continue

            file_no += 1
            fname = f"pages/{file_no:04d}.html"
            fpath = os.path.join(out_dir, fname)
            with open(fpath, "wb") as f:
                f.write(res.data)

            saved.append((file_no, res.src_url))

    # index.txt: номер файла и ссылка
    index_path = os.path.join(out_dir, "index.txt")
    with open(index_path, "w", encoding="utf-8", newline="\n") as f:
        for n, url in sorted(saved, key=lambda x: x[0]):
            f.write(f"{n:04d}\t{url}\n")

    # лог ошибок/пропусков
    if skipped:
        with open(os.path.join(out_dir, "skipped.log"), "w", encoding="utf-8", newline="\n") as f:
            for line in skipped:
                f.write(line + "\n")

    print(f"[OK] saved: {len(saved)} pages -> {out_dir}")
    print(f"[OK] index: {index_path}")
    if skipped:
        print(f"[INFO] skipped: {len(skipped)} (see {os.path.join(out_dir, 'skipped.log')})")

    if len(saved) < need:
        print(f"[WARN] need={need}, but saved only {len(saved)}.")


def main() -> None:
    p = argparse.ArgumentParser(description="Download raw HTML pages from urls.txt and build index.txt")
    p.add_argument("--urls", required=True, help="Path to urls.txt")
    p.add_argument("--out", default="dump", help="Output directory")
    p.add_argument("--need", type=int, default=100, help="How many pages must be saved")
    p.add_argument("--workers", type=int, default=6, help="Parallel downloads")
    p.add_argument("--delay", type=float, default=0.6, help="Per-host delay seconds")
    p.add_argument("--timeout", type=int, default=30, help="HTTP timeout seconds")
    p.add_argument("--user-agent", default=DEFAULT_UA, help="User-Agent header")
    args = p.parse_args()

    urls = read_urls(args.urls)
    if not urls:
        print("[ERROR] urls.txt is empty or contains only invalid lines", file=sys.stderr)
        sys.exit(1)

    crawl(
        urls=urls,
        out_dir=args.out,
        need=args.need,
        workers=args.workers,
        delay=args.delay,
        timeout=args.timeout,
        user_agent=args.user_agent,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nABORTED")
