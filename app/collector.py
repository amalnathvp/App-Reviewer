import re
import json
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Dict, Any, List, Optional
from google_play_scraper import app as gp_app, reviews as gp_reviews, search as gp_search, Sort

class ReviewCollector:
    """
    Collects mobile app metadata and customer reviews from Google Play Store
    and Apple App Store, packaging them into the standardized AI Agent input contract.
    """

    @staticmethod
    def extract_google_play_id(input_str: str) -> Optional[str]:
        if not input_str:
            return None
        input_str = input_str.strip()
        # Check if URL with id=
        match = re.search(r'[?&]id=([a-zA-Z0-9._]+)', input_str)
        if match:
            return match.group(1)
        # Check if already a package name like com.company.app
        if re.match(r'^[a-zA-Z0-9_]+(\.[a-zA-Z0-9_]+)+$', input_str):
            return input_str
        return None

    @staticmethod
    def extract_apple_app_id(input_str: str) -> Optional[str]:
        if not input_str:
            return None
        input_str = input_str.strip()
        # Check if URL with id123456789
        match = re.search(r'id(\d+)', input_str)
        if match:
            return match.group(1)
        # Check if purely digits
        if input_str.isdigit():
            return input_str
        return None

    @staticmethod
    def search_google_play(app_name: str, country: str = "us", lang: str = "en") -> Optional[str]:
        try:
            results = gp_search(app_name, lang=lang, country=country)
            if results and len(results) > 0:
                return results[0].get("appId")
        except Exception as e:
            print(f"Error searching Google Play for {app_name}: {e}")
        return None

    @staticmethod
    def search_apple_store(app_name: str, country: str = "us") -> Optional[Dict[str, Any]]:
        try:
            query = urllib.parse.quote(app_name)
            url = f"https://itunes.apple.com/search?term={query}&entity=software&country={country}&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as res:
                data = json.loads(res.read().decode("utf-8"))
                results = data.get("results", [])
                if results:
                    return results[0]
        except Exception as e:
            print(f"Error searching Apple Store for {app_name}: {e}")
        return None

    @classmethod
    def fetch_google_play(cls, package_id: str, count: int = 50, country: str = "us", lang: str = "en") -> Dict[str, Any]:
        meta = {
            "name": package_id,
            "package_id": package_id,
            "app_store_id": "",
            "category": "Mobile App",
            "description": "",
            "rating": None,
            "review_count": None
        }
        reviews_list = []

        try:
            app_info = gp_app(package_id, lang=lang, country=country)
            meta["name"] = app_info.get("title", package_id)
            meta["category"] = app_info.get("genre", "Mobile App")
            desc = app_info.get("description", "")
            meta["description"] = desc[:500] if desc else ""
            meta["rating"] = round(float(app_info.get("score", 0.0)), 2) if app_info.get("score") else None
            meta["review_count"] = app_info.get("reviews")
        except Exception as e:
            print(f"Warning: Could not fetch Google Play app details for {package_id}: {e}")

        try:
            result, _ = gp_reviews(
                package_id,
                lang=lang,
                country=country,
                sort=Sort.NEWEST,
                count=count
            )
            for r in result:
                dt_str = str(r.get("at", datetime.utcnow().strftime("%Y-%m-%d")))
                if len(dt_str) > 10:
                    dt_str = dt_str[:10]
                reviews_list.append({
                    "platform": "google_play",
                    "rating": int(r.get("score", 1)),
                    "review": str(r.get("content", "")).strip(),
                    "date": dt_str,
                    "version": str(r.get("reviewCreatedVersion") or "N/A"),
                    "language": lang,
                    "helpful_count": int(r.get("thumbsUpCount", 0))
                })
        except Exception as e:
            print(f"Error fetching Google Play reviews for {package_id}: {e}")

        return {"app": meta, "reviews": reviews_list}

    @classmethod
    def fetch_apple_store(cls, app_id: str, country: str = "us") -> Dict[str, Any]:
        meta = {
            "name": f"iOS App ({app_id})",
            "package_id": "",
            "app_store_id": str(app_id),
            "category": "iOS Application",
            "description": "",
            "rating": None,
            "review_count": None
        }
        reviews_list = []

        # 1. Fetch metadata via iTunes lookup
        try:
            lookup_url = f"https://itunes.apple.com/lookup?id={app_id}&country={country}"
            req = urllib.request.Request(lookup_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as res:
                data = json.loads(res.read().decode("utf-8"))
                if data.get("results"):
                    info = data["results"][0]
                    meta["name"] = info.get("trackName", meta["name"])
                    meta["category"] = info.get("primaryGenreName", "iOS Application")
                    desc = info.get("description", "")
                    meta["description"] = desc[:500] if desc else ""
                    meta["rating"] = round(float(info.get("averageUserRating", 0.0)), 2) if info.get("averageUserRating") else None
                    meta["review_count"] = info.get("userRatingCount")
        except Exception as e:
            print(f"Lookup error for Apple App {app_id}: {e}")

        # 2. Fetch reviews from Apple webpage embedded state
        try:
            web_url = f"https://apps.apple.com/{country}/app/id{app_id}"
            req = urllib.request.Request(web_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            with urllib.request.urlopen(req, timeout=10) as res:
                html = res.read().decode("utf-8", errors="ignore")
                scripts = re.findall(r'<script[^>]+type=[\'"]application/json[\'"][^>]*>(.*?)</script>', html, re.DOTALL)
                for s in scripts:
                    try:
                        parsed = json.loads(s)
                        # Helper recursive search for shelf
                        def find_all_reviews(obj):
                            if isinstance(obj, dict):
                                if "contentType" in obj and obj.get("contentType") == "productReview" and "items" in obj:
                                    return obj.get("items", [])
                                for v in obj.values():
                                    res = find_all_reviews(v)
                                    if res:
                                        return res
                            elif isinstance(obj, list):
                                for item in obj:
                                    res = find_all_reviews(item)
                                    if res:
                                        return res
                            return None

                        items = find_all_reviews(parsed)
                        if items:
                            for item in items:
                                rev = item.get("review", {})
                                if rev and rev.get("contents"):
                                    dt = str(rev.get("date", datetime.utcnow().strftime("%Y-%m-%d")))
                                    if len(dt) > 10:
                                        dt = dt[:10]
                                    reviews_list.append({
                                        "platform": "app_store",
                                        "rating": int(rev.get("rating", 1)),
                                        "review": str(rev.get("contents", "")).strip(),
                                        "date": dt,
                                        "version": "Latest",
                                        "language": "en",
                                        "helpful_count": 0
                                    })
                            break
                    except Exception:
                        continue
        except Exception as e:
            print(f"Error fetching web reviews for Apple App {app_id}: {e}")

        return {"app": meta, "reviews": reviews_list}

    @classmethod
    def collect(
        cls,
        app_name: Optional[str] = None,
        google_play_url: Optional[str] = None,
        apple_store_url: Optional[str] = None,
        review_limit: int = 60,
        country: str = "us"
    ) -> Dict[str, Any]:
        """
        Orchestrates retrieval across Google Play and Apple App Store
        returning standard structured JSON input.
        """
        final_app_meta: Dict[str, Any] = {
            "name": app_name or "Mobile App",
            "package_id": "",
            "app_store_id": "",
            "category": "Mobile App",
            "description": "",
            "rating": None,
            "review_count": None
        }
        all_reviews: List[Dict[str, Any]] = []

        gp_pkg = cls.extract_google_play_id(google_play_url) if google_play_url else None
        ios_id = cls.extract_apple_app_id(apple_store_url) if apple_store_url else None

        # If only app name provided, attempt store resolution
        if not gp_pkg and not ios_id and app_name:
            gp_pkg = cls.search_google_play(app_name, country=country)
            apple_res = cls.search_apple_store(app_name, country=country)
            if apple_res:
                ios_id = str(apple_res.get("trackId", ""))
                if not final_app_meta["name"] or final_app_meta["name"] == "Mobile App":
                    final_app_meta["name"] = apple_res.get("trackName", app_name)
        elif app_name:
            if not gp_pkg:
                gp_pkg = cls.search_google_play(app_name, country=country)
            if not ios_id:
                apple_res = cls.search_apple_store(app_name, country=country)
                if apple_res:
                    ios_id = str(apple_res.get("trackId", ""))

        # 1. Fetch Google Play if available
        if gp_pkg:
            gp_data = cls.fetch_google_play(gp_pkg, count=review_limit, country=country)
            all_reviews.extend(gp_data["reviews"])
            final_app_meta["package_id"] = gp_pkg
            if gp_data["app"].get("name"):
                final_app_meta["name"] = gp_data["app"]["name"]
            if gp_data["app"].get("category"):
                final_app_meta["category"] = gp_data["app"]["category"]
            if gp_data["app"].get("description"):
                final_app_meta["description"] = gp_data["app"]["description"]
            final_app_meta["rating"] = gp_data["app"].get("rating")
            final_app_meta["review_count"] = gp_data["app"].get("review_count")

        # 2. Fetch Apple App Store if available
        if ios_id:
            ios_data = cls.fetch_apple_store(ios_id, country=country)
            all_reviews.extend(ios_data["reviews"])
            final_app_meta["app_store_id"] = ios_id
            if not final_app_meta["package_id"]:
                final_app_meta["name"] = ios_data["app"].get("name", final_app_meta["name"])
                final_app_meta["category"] = ios_data["app"].get("category", final_app_meta["category"])
                final_app_meta["description"] = ios_data["app"].get("description", final_app_meta["description"])
                final_app_meta["rating"] = ios_data["app"].get("rating")
                final_app_meta["review_count"] = ios_data["app"].get("review_count")

        return {
            "app": final_app_meta,
            "reviews": all_reviews
        }

    @classmethod
    def auto_collect(cls, query_or_url: str, review_limit: int = 80, country: str = "us") -> Dict[str, Any]:
        """
        Takes a single input (App Name, Google Play URL, Apple App Store URL, or Package ID)
        and automatically resolves and retrieves customer feedback.
        """
        query_or_url = (query_or_url or "").strip()
        if not query_or_url:
            return {"app": {"name": "Unknown"}, "reviews": []}

        # Case 1: Google Play URL or package name
        gp_id = cls.extract_google_play_id(query_or_url)
        # Case 2: Apple App Store URL or ID
        ios_id = cls.extract_apple_app_id(query_or_url)

        if gp_id and not ios_id:
            # We have Google Play ID; check if we can get app name to find iOS parity
            app_meta = cls.fetch_google_play(gp_id, count=review_limit, country=country)
            app_name = app_meta["app"].get("name")
            if app_name and app_name != gp_id:
                apple_res = cls.search_apple_store(app_name, country=country)
                if apple_res:
                    ios_id = str(apple_res.get("trackId", ""))
            return cls.collect(
                app_name=app_name or gp_id,
                google_play_url=gp_id,
                apple_store_url=ios_id,
                review_limit=review_limit,
                country=country
            )

        if ios_id and not gp_id:
            # We have iOS ID; find Google Play parity
            ios_meta = cls.fetch_apple_store(ios_id, country=country)
            app_name = ios_meta["app"].get("name")
            if app_name:
                gp_id = cls.search_google_play(app_name, country=country)
            return cls.collect(
                app_name=app_name,
                google_play_url=gp_id,
                apple_store_url=ios_id,
                review_limit=review_limit,
                country=country
            )

        # Case 3: App Name provided
        return cls.collect(
            app_name=query_or_url,
            google_play_url=None,
            apple_store_url=None,
            review_limit=review_limit,
            country=country
        )
