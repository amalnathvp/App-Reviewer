import re
import math
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict, Counter

class PMAgent:
    """
    AI Product Management Intelligence Agent
    Analyzes unstructured mobile application reviews into actionable PM insights.
    Strictly follows evidence-based rules and the 14-step framework.
    """

    # Regex patterns for PII protection
    EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
    PHONE_REGEX = re.compile(r'(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}')

    # Meaningless one-word reviews
    MEANINGLESS_WORDS = {"good", "bad", "nice", "ok", "cool", "super", "great", "worst", "fine", "app", "best", "helpful", "like"}

    # Keyword taxonomies for thematic clustering and problem detection
    THEME_KEYWORDS = {
        "Authentication & Onboarding": ["login", "log in", "signin", "sign in", "signup", "sign up", "password", "otp", "verify", "verification", "register", "registration", "account", "onboarding"],
        "Performance & Latency": ["slow", "lag", "laggy", "freeze", "froze", "hang", "hanging", "battery", "drain", "heat", "overheating", "loading", "buffer", "buffering", "smooth", "fast", "speed"],
        "Stability & Crashes": ["crash", "crashing", "crashed", "bug", "glitch", "error", "black screen", "blank screen", "closes", "force close", "stuck", "broken"],
        "UI & Navigation (UX)": ["ui", "ux", "interface", "design", "confusing", "cluttered", "font", "dark mode", "theme", "layout", "button", "navigate", "navigation", "gestures", "intuitive", "clean"],
        "Pricing, Subscriptions & Ads": ["ad", "ads", "advert", "expensive", "subscription", "price", "paywall", "cost", "money", "greedy", "refund", "charge", "charged", "billing", "free", "premium"],
        "Missing Features & Enhancements": ["please add", "add", "wish", "feature", "bring back", "missing", "option", "need", "allow", "support", "custom", "export", "filter", "search", "widget", "sync"],
        "Content & Media Quality": ["content", "audio", "video", "sound", "volume", "music", "podcast", "article", "lesson", "question", "answers", "database", "catalog"],
        "Notifications & Background": ["notification", "notifications", "alert", "push", "reminder", "badge", "background", "offline", "sync"],
        "Customer Support & Reliability": ["support", "customer service", "help", "email", "reply", "unresponsive", "fix this", "update ruined", "update broke"]
    }

    # Sentiment lexicons
    POSITIVE_WORDS = {
        "love", "amazing", "great", "excellent", "best", "awesome", "fantastic", "wonderful", "perfect",
        "smooth", "helpful", "easy", "intuitive", "clean", "favorite", "superb", "brilliant", "enjoy",
        "fast", "reliable", "flawless", "pleasure", "recommend", "satisfied", "impressive", "outstanding"
    }
    NEGATIVE_WORDS = {
        "hate", "terrible", "awful", "worst", "horrible", "bad", "poor", "useless", "trash", "garbage",
        "broken", "crash", "crashes", "crashing", "bug", "bugs", "glitch", "slow", "lag", "freeze",
        "unusable", "waste", "annoying", "frustrated", "disappointed", "ruined", "greedy", "scam",
        "stuck", "ridiculous", "regret", "unacceptable", "disaster"
    }

    @classmethod
    def clean_reviews(cls, raw_reviews: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Step 1: Review Cleaning
        Deduplicate exact and near-duplicates, remove spam/empty/meaningless, mask PII.
        """
        seen_texts = set()
        seen_fingerprints = set()
        cleaned: List[Dict[str, Any]] = []
        duplicates_removed = 0
        spam_removed = 0
        platforms_present = set()

        for item in raw_reviews:
            raw_text = str(item.get("review", "")).strip()
            platform = str(item.get("platform", "unknown"))
            platforms_present.add(platform)

            if not raw_text:
                spam_removed += 1
                continue

            # Mask PII
            sanitized = cls.EMAIL_REGEX.sub("[EMAIL REDACTED]", raw_text)
            sanitized = cls.PHONE_REGEX.sub("[PHONE REDACTED]", sanitized)

            # Check normalized tokens
            tokens = re.findall(r'[a-zA-Z0-9]+', sanitized.lower())
            if not tokens:
                spam_removed += 1
                continue

            # Filter meaningless ultra-short reviews
            if len(tokens) <= 2 and all(t in cls.MEANINGLESS_WORDS for t in tokens):
                spam_removed += 1
                continue

            # Deduplication
            normalized_str = " ".join(tokens)
            if normalized_str in seen_texts:
                duplicates_removed += 1
                continue

            # Near-duplicate fingerprint (token set of longer words)
            token_fingerprint = frozenset([t for t in tokens if len(t) > 3])
            if len(token_fingerprint) >= 4 and token_fingerprint in seen_fingerprints:
                duplicates_removed += 1
                continue

            seen_texts.add(normalized_str)
            if len(token_fingerprint) >= 4:
                seen_fingerprints.add(token_fingerprint)

            cleaned_item = dict(item)
            cleaned_item["review"] = sanitized
            cleaned_item["tokens"] = tokens
            cleaned.append(cleaned_item)

        quality_meta = {
            "total_reviews_received": len(raw_reviews),
            "reviews_analyzed": len(cleaned),
            "duplicates_removed": duplicates_removed,
            "spam_removed": spam_removed,
            "platforms": sorted(list(platforms_present))
        }
        return cleaned, quality_meta

    @classmethod
    def analyze_sentiment(cls, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Step 2: Sentiment Analysis & Intensity
        Classifies positive, negative, neutral, mixed with intensity.
        """
        if not reviews:
            return {
                "positive": 0, "negative": 0, "neutral": 0, "mixed": 0,
                "summary": "Insufficient evidence. No reviews analyzed."
            }

        counts = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
        total = len(reviews)

        for rev in reviews:
            rating = rev.get("rating", 3)
            tokens = set(rev.get("tokens", []))
            pos_overlap = len(tokens.intersection(cls.POSITIVE_WORDS))
            neg_overlap = len(tokens.intersection(cls.NEGATIVE_WORDS))

            if rating >= 4:
                if neg_overlap >= 2 and pos_overlap >= 1:
                    classification = "mixed"
                else:
                    classification = "positive"
            elif rating <= 2:
                if pos_overlap >= 2 and neg_overlap >= 1:
                    classification = "mixed"
                else:
                    classification = "negative"
            else: # rating == 3
                if pos_overlap > neg_overlap:
                    classification = "positive"
                elif neg_overlap > pos_overlap:
                    classification = "negative"
                elif pos_overlap > 0 and neg_overlap > 0:
                    classification = "mixed"
                else:
                    classification = "neutral"

            # Determine intensity
            word_count = len(rev.get("tokens", []))
            has_strong_words = bool(tokens.intersection({"hate", "worst", "unusable", "disaster", "best", "love", "amazing"}))
            if has_strong_words or word_count > 35:
                intensity = "High"
            elif word_count > 12:
                intensity = "Medium"
            else:
                intensity = "Low"

            rev["sentiment"] = classification
            rev["sentiment_intensity"] = intensity
            counts[classification] += 1

        pos_pct = round((counts["positive"] / total) * 100, 1)
        neg_pct = round((counts["negative"] / total) * 100, 1)
        neu_pct = round((counts["neutral"] / total) * 100, 1)
        mix_pct = round((counts["mixed"] / total) * 100, 1)

        summary_desc = (
            f"Analyzed {total} verified user reviews. Sentiment breakdown: {pos_pct}% Positive, "
            f"{neg_pct}% Negative, {neu_pct}% Neutral, and {mix_pct}% Mixed. "
            f"{'Positive sentiment dominates user perception.' if pos_pct >= 55 else 'Noticeable negative friction indicates immediate intervention is required.' if neg_pct >= 30 else 'Sentiment is balanced across the user base.'}"
        )

        return {
            "positive": pos_pct,
            "negative": neg_pct,
            "neutral": neu_pct,
            "mixed": mix_pct,
            "summary": summary_desc
        }

    @classmethod
    def extract_problems(cls, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Step 3: User Problems Extraction
        Identifies actual problems, root causes, severity, impact, and evidence.
        """
        problem_clusters = defaultdict(list)

        for rev in reviews:
            text = rev.get("review", "")
            text_lower = text.lower()
            rating = rev.get("rating", 3)

            # We focus on negative or mixed reviews or low ratings for problems
            if rating > 3 and rev.get("sentiment") != "mixed":
                continue

            matched = False
            # Cluster by problem patterns
            if any(k in text_lower for k in ["crash", "crashing", "crashed", "force close", "closes automatically", "shut down"]):
                problem_clusters["App Crash & Stability Failures"].append(rev)
                matched = True
            elif any(k in text_lower for k in ["login", "log in", "otp", "password", "verification", "sign in", "signin", "cant log"]):
                problem_clusters["Authentication & Account Access Blockers"].append(rev)
                matched = True
            elif any(k in text_lower for k in ["slow", "lag", "freeze", "loading forever", "stuck on screen", "battery", "drain"]):
                problem_clusters["Sluggish Performance & High Latency"].append(rev)
                matched = True
            elif any(k in text_lower for k in ["ad", "ads", "advert", "pop up", "too many ads", "commercials"]):
                problem_clusters["Intrusive Ad Experience & Interstitial Clutter"].append(rev)
                matched = True
            elif any(k in text_lower for k in ["paywall", "subscription", "expensive", "charged", "billing", "money", "price hike"]):
                problem_clusters["Aggressive Monetization & Subscription Friction"].append(rev)
                matched = True
            elif any(k in text_lower for k in ["ui", "layout", "confusing", "cluttered", "hard to navigate", "update ruined", "design"]):
                problem_clusters["Confusing UI Hierarchy & Navigation Friction"].append(rev)
                matched = True
            elif any(k in text_lower for k in ["sync", "offline", "lost progress", "lost data", "disappeared", "backup"]):
                problem_clusters["Data Loss & Cross-Device Sync Failures"].append(rev)
                matched = True
            elif any(k in text_lower for k in ["search", "cant find", "filter", "sorting", "search not working"]):
                problem_clusters["Search Inefficiency & Inadequate Discovery Filters"].append(rev)
                matched = True
            elif any(k in text_lower for k in ["notification", "notifications", "spamming notifications", "silent"]):
                problem_clusters["Disruptive Notification Frequency"].append(rev)
                matched = True
            
            if not matched and rating <= 2 and len(rev.get("tokens", [])) >= 5:
                problem_clusters["General Core Functionality & Usability Defects"].append(rev)

        problems: List[Dict[str, Any]] = []
        total_reviews = max(len(reviews), 1)

        # Persona & root cause definitions
        meta_configs = {
            "App Crash & Stability Failures": {
                "user_type": "Daily active mobile user across diverse device configurations",
                "user_goal": "Access app features reliably without interruption or sudden app termination",
                "severity": 5, "impact": 5,
                "root_cause": "Unhandled memory pressure, unhandled exceptions during asynchronous API calls, or version regression on newer OS updates."
            },
            "Authentication & Account Access Blockers": {
                "user_type": "Onboarding new users and returning authenticated subscribers",
                "user_goal": "Seamlessly verify credentials and access personal workspace/content",
                "severity": 5, "impact": 5,
                "root_cause": "SMS gateway latency/timeouts during OTP delivery, expired auth tokens, or broken OAuth token handshakes."
            },
            "Sluggish Performance & High Latency": {
                "user_type": "Power users with extensive data and users on mid-range devices",
                "user_goal": "Navigate quickly with snappy response times and fluid transitions",
                "severity": 4, "impact": 4,
                "root_cause": "Unoptimized main-thread operations, heavy client-side asset rendering, or unindexed local database queries."
            },
            "Intrusive Ad Experience & Interstitial Clutter": {
                "user_type": "Free tier users engaging with core workflow tasks",
                "user_goal": "Complete primary task without aggressive interruptions",
                "severity": 3, "impact": 4,
                "root_cause": "Aggressive ad mediation triggers firing immediately after basic user interactions rather than at natural task breaks."
            },
            "Aggressive Monetization & Subscription Friction": {
                "user_type": "Prospective buyers and long-term loyal users",
                "user_goal": "Understand transparent value proposition before committing financially",
                "severity": 3, "impact": 4,
                "root_cause": "Abrupt paywalls locking previously free features without clear value tier communication."
            },
            "Confusing UI Hierarchy & Navigation Friction": {
                "user_type": "Casual users and users adapting to recent redesigns",
                "user_goal": "Locate desired tools and content intuitively with minimal cognitive load",
                "severity": 3, "impact": 3,
                "root_cause": "Information architecture overhaul that buried high-frequency shortcuts or deviated from standard mobile design paradigms."
            },
            "Data Loss & Cross-Device Sync Failures": {
                "user_type": "Productive users relying on multi-device workflows",
                "user_goal": "Preserve work progress and synchronize data reliably in real time",
                "severity": 5, "impact": 5,
                "root_cause": "Flawed conflict-resolution logic during local-to-cloud synchronization or uncommitted background transactions."
            },
            "Search Inefficiency & Inadequate Discovery Filters": {
                "user_type": "Users searching within expanding catalogs or libraries",
                "user_goal": "Pinpoint relevant items instantly through accurate query matches and filters",
                "severity": 3, "impact": 3,
                "root_cause": "Substring query matching lacking fuzzy search, relevance ranking, or granular parameter filters."
            },
            "Disruptive Notification Frequency": {
                "user_type": "Engaged mobile users",
                "user_goal": "Receive timely, high-value alerts without promotional noise",
                "severity": 2, "impact": 2,
                "root_cause": "Hardcoded re-engagement push schedules lacking user preference controls or activity-aware throttling."
            },
            "General Core Functionality & Usability Defects": {
                "user_type": "General application users",
                "user_goal": "Achieve intended utility without unhandled edge-case failures",
                "severity": 3, "impact": 3,
                "root_cause": "Gaps in regression testing across edge operating environments."
            }
        }

        for problem_name, rev_list in problem_clusters.items():
            count = len(rev_list)
            if count == 0:
                continue

            config = meta_configs.get(problem_name, {
                "user_type": "Mobile application user",
                "user_goal": "Seamless product operation",
                "severity": 3, "impact": 3,
                "root_cause": "Underlying software logic defect."
            })

            # Calculate frequency score (1 to 5)
            ratio = count / total_reviews
            if ratio >= 0.25:
                freq_score = 5
                freq_label = "Very Frequent"
            elif ratio >= 0.15:
                freq_score = 4
                freq_label = "Frequent"
            elif ratio >= 0.08:
                freq_score = 3
                freq_label = "Moderate"
            elif count >= 2:
                freq_score = 2
                freq_label = "Rare"
            else:
                freq_score = 1
                freq_label = "Very Rare"

            severity = config["severity"]
            impact = config["impact"]

            # Collect versions, platforms, and churn risk for this problem
            version_counter = Counter()
            platform_counter = Counter()
            churn_mentions_count = 0

            for r in rev_list:
                ver = r.get("version", "").strip()
                plt = "Android" if r.get("platform") == "google_play" else "iOS"
                platform_counter[plt] += 1
                if ver and ver not in ("N/A", "None", ""):
                    clean_v = ver if ver.startswith("v") else f"v{ver}"
                    version_counter[f"{clean_v} ({plt})"] += 1
                else:
                    version_counter[f"{plt} (Current)"] += 1

                txt_lower = r.get("review", "").lower()
                if any(w in txt_lower for w in ["uninstall", "uninstalled", "deleting", "deleted", "cancel", "canceling", "switch", "leaving", "gave up"]):
                    churn_mentions_count += 1

            top_affected_versions = [v for v, _ in version_counter.most_common(3)]
            churn_risk_level = "High Risk" if churn_mentions_count >= 2 else ("Moderate Risk" if churn_mentions_count == 1 else "Low Risk")
            priority_score_val = impact * freq_score * severity
            release_verdict_str = "Blocker: Requires Immediate Hotfix" if (severity >= 4 and impact >= 4 and priority_score_val >= 25) else ("High Priority for Next Sprint" if priority_score_val >= 18 else "Backlog Improvement")

            # Collect genuine quotes
            evidence = []
            for r in rev_list[:4]:
                txt = r.get("review", "")
                if len(txt) > 140:
                    txt = txt[:137] + "..."
                ver_tag = r.get("version")
                ver_str = f" [v{ver_tag}]" if ver_tag and ver_tag != "N/A" else ""
                evidence.append(f'"{txt}" (Rating: {r.get("rating")} Stars{ver_str})')

            problems.append({
                "problem": problem_name,
                "description": f"Users consistently report {problem_name.lower()} preventing them from achieving their core objective. Affects {count} verified review(s) ({round(ratio*100, 1)}% of analyzed feedback).",
                "user_type": config["user_type"],
                "user_goal": config["user_goal"],
                "frequency": f"{freq_label} ({count} mentions, {round(ratio*100, 1)}%)",
                "frequency_score": freq_score,
                "severity": severity,
                "impact": impact,
                "priority_score": priority_score_val,
                "platforms_affected": list(platform_counter.keys()),
                "affected_versions": top_affected_versions,
                "platform_breakdown": dict(platform_counter),
                "churn_risk": churn_risk_level,
                "release_verdict": release_verdict_str,
                "evidence": evidence,
                "possible_root_cause": config["root_cause"]
            })

        # Sort descending by Priority Score
        problems.sort(key=lambda p: p["priority_score"], reverse=True)
        return problems

    @classmethod
    def extract_positive_feedback(cls, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Step 4: Positive Feedback Synthesis
        Finds features users love, UX/UI praises, performance, pricing, reliability.
        """
        pos_clusters = defaultdict(list)

        for rev in reviews:
            if rev.get("rating", 1) < 4:
                continue

            text = rev.get("review", "").lower()
            if any(k in text for k in ["easy", "simple", "intuitive", "user friendly", "convenient"]):
                pos_clusters["Intuitive Usability & Ease of Use"].append(rev)
            if any(k in text for k in ["clean", "design", "ui", "interface", "beautiful", "look", "aesthetic"]):
                pos_clusters["Aesthetic & Clean Modern UI"].append(rev)
            if any(k in text for k in ["fast", "smooth", "quick", "responsive", "lightweight"]):
                pos_clusters["Snappy Responsiveness & Smooth Performance"].append(rev)
            if any(k in text for k in ["learn", "study", "content", "helpful", "audio", "music", "game", "features"]):
                pos_clusters["High-Utility Core Value & Functional Delivery"].append(rev)
            if any(k in text for k in ["free", "worth", "price", "affordable", "value"]):
                pos_clusters["Strong Value Proposition & Fair Pricing"].append(rev)
            if any(k in text for k in ["support", "update", "developers", "listen"]):
                pos_clusters["Responsive Developer Updates & Support"].append(rev)

        results: List[Dict[str, Any]] = []
        for aspect, rev_list in pos_clusters.items():
            quotes = []
            for r in rev_list[:3]:
                txt = r.get("review", "")
                if len(txt) > 130:
                    txt = txt[:127] + "..."
                quotes.append(f'"{txt}" ({r.get("rating")}★)')

            results.append({
                "theme": aspect,
                "mentions": len(rev_list),
                "sentiment_drivers": f"Users actively cite this aspect as a key driver of high customer satisfaction.",
                "evidence": quotes
            })

        results.sort(key=lambda x: x["mentions"], reverse=True)
        return results

    @classmethod
    def extract_feature_requests(cls, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Step 5: Feature Requests Extraction
        Extracts explicit requests and implied feature opportunities.
        """
        explicit_patterns = ["please add", "can you add", "add a", "would be nice", "wish there was", "should have", "bring back", "needs a"]
        requests: List[Dict[str, Any]] = []
        total_revs = max(len(reviews), 1)

        request_catalog = defaultdict(list)

        for rev in reviews:
            text = rev.get("review", "")
            t_lower = text.lower()
            is_explicit = any(p in t_lower for p in explicit_patterns)

            if "dark mode" in t_lower or "black theme" in t_lower:
                request_catalog["Dark Mode & Custom Theme Support"].append((rev, is_explicit))
            elif "offline" in t_lower or "no internet" in t_lower:
                request_catalog["Full Offline Mode & Local Caching"].append((rev, is_explicit))
            elif "widget" in t_lower or "widgets" in t_lower:
                request_catalog["Home Screen & Lock Screen Widgets"].append((rev, is_explicit))
            elif "sync" in t_lower or "cloud" in t_lower or "cross platform" in t_lower:
                request_catalog["Seamless Multi-Device Cloud Synchronization"].append((rev, is_explicit))
            elif "export" in t_lower or "pdf" in t_lower or "csv" in t_lower:
                request_catalog["Data Export & Sharing Capabilities (PDF/CSV)"].append((rev, is_explicit))
            elif "filter" in t_lower or "sort" in t_lower or "folder" in t_lower or "organize" in t_lower:
                request_catalog["Enhanced Organization, Folders & Granular Filters"].append((rev, is_explicit))
            elif "notification" in t_lower and ("control" in t_lower or "custom" in t_lower or "schedule" in t_lower):
                request_catalog["Custom Notification Frequency & Quiet Hours"].append((rev, is_explicit))

        for feat_name, rev_tuples in request_catalog.items():
            count = len(rev_tuples)
            explicit_count = sum(1 for _, exp in rev_tuples if exp)
            req_type = "Explicit Feature Request" if explicit_count > 0 else "Implied Feature Opportunity"
            platforms = list(set([r.get("platform", "google_play") for r, _ in rev_tuples]))
            evidence = []
            for r, _ in rev_tuples[:3]:
                txt = r.get("review", "")
                if len(txt) > 130:
                    txt = txt[:127] + "..."
                evidence.append(f'"{txt}"')

            requests.append({
                "feature": feat_name,
                "type": req_type,
                "user_need": f"Users desire {feat_name.lower()} to improve productivity, control, and accessibility.",
                "number_of_mentions": count,
                "percentage_of_reviews": f"{round((count / total_revs) * 100, 1)}%",
                "platforms": platforms,
                "expected_impact": "High" if count >= 3 else "Medium",
                "evidence": evidence
            })

        requests.sort(key=lambda x: x["number_of_mentions"], reverse=True)
        return requests

    @classmethod
    def thematic_clustering(cls, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Step 6: Thematic Clustering
        Clusters reviews into meaningful product themes.
        """
        theme_buckets = defaultdict(list)

        for rev in reviews:
            text_lower = rev.get("review", "").lower()
            matched = False
            for theme, keywords in cls.THEME_KEYWORDS.items():
                if any(kw in text_lower for kw in keywords):
                    theme_buckets[theme].append(rev)
                    matched = True
            if not matched:
                theme_buckets["General Product Feedback"].append(rev)

        themes_list = []
        total = max(len(reviews), 1)

        for theme, rev_list in theme_buckets.items():
            count = len(rev_list)
            ratings = [r.get("rating", 3) for r in rev_list]
            avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0
            pos = sum(1 for r in rev_list if r.get("rating", 3) >= 4)
            neg = sum(1 for r in rev_list if r.get("rating", 3) <= 2)

            dominant_sentiment = "Positive" if pos > neg else ("Negative" if neg > pos else "Neutral")

            sample_quotes = []
            for r in rev_list[:2]:
                q = r.get("review", "")
                if len(q) > 110:
                    q = q[:107] + "..."
                sample_quotes.append(f'"{q}"')

            themes_list.append({
                "theme_name": theme,
                "review_count": count,
                "percentage": f"{round((count / total) * 100, 1)}%",
                "average_rating": avg_rating,
                "dominant_sentiment": dominant_sentiment,
                "sample_evidence": sample_quotes
            })

        themes_list.sort(key=lambda t: t["review_count"], reverse=True)
        return themes_list

    @classmethod
    def generate_product_opportunities(cls, prioritized_problems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Step 8: Product Opportunities
        Converts highest-priority problems into structured product opportunities.
        """
        opportunities = []

        for p in prioritized_problems[:5]:
            prob_title = p["problem"]
            freq = p.get("frequency_score", 1)
            severity = p.get("severity", 3)

            # Confidence based on evidence volume
            confidence = "High" if freq >= 3 else ("Medium" if freq >= 2 else "Low")

            # Determine effort & solution
            if "Crash" in prob_title or "Stability" in prob_title:
                opp_name = "Hardened Application Reliability & Crash-Free Architecture"
                solution = "Implement automated Sentry error monitoring, graceful crash fallbacks, and memory leak mitigation in native render layers."
                effort = "Medium"
                impact = "Very High"
            elif "Auth" in prob_title or "Login" in prob_title:
                opp_name = "Zero-Friction Authentication & Session Persistence Overhaul"
                solution = "Introduce multi-provider OAuth (Google/Apple Sign-In), biometric unlock (FaceID/Fingerprint), and redundant SMS/WhatsApp OTP gateways."
                effort = "Low"
                impact = "Very High"
            elif "Performance" in prob_title or "Latency" in prob_title:
                opp_name = "Sub-Second Performance Optimization & Asset Virtualization"
                solution = "Adopt virtualized scrolling lists, lazy load off-screen media, and cache frequently accessed network responses locally."
                effort = "Medium"
                impact = "High"
            elif "Ad" in prob_title or "Monetization" in prob_title:
                opp_name = "Balanced Monetization Engine & Rewarded Ad Cadence"
                solution = "Implement ad frequency capping, replace intrusive interstitials with opt-in rewarded ads, and offer a transparent budget ad-free tier."
                effort = "Low"
                impact = "High"
            elif "UI" in prob_title or "Navigation" in prob_title:
                opp_name = "Ergonomic Navigation Redesign & Task-Oriented IA"
                solution = "Re-architect main tab bar, standardize back-stack navigation, and introduce contextual in-app guidance for key flows."
                effort = "Medium"
                impact = "Medium"
            elif "Sync" in prob_title or "Data" in prob_title:
                opp_name = "Conflict-Free Offline-First Data Synchronization"
                solution = "Implement CRDT-based local SQLite caching with background sync queues when internet connectivity restores."
                effort = "High"
                impact = "Very High"
            else:
                opp_name = f"Targeted UX Resolution for {prob_title}"
                solution = "Deploy targeted bug fixes and validate through controlled A/B canary testing."
                effort = "Low"
                impact = "Medium"

            opportunities.append({
                "opportunity": opp_name,
                "user_problem": p["description"],
                "target_user": p["user_type"],
                "user_need": p["user_goal"],
                "evidence": p["evidence"][:2],
                "potential_solution": solution,
                "expected_impact": impact,
                "estimated_effort": effort,
                "priority": "High" if p["priority_score"] >= 20 else "Medium",
                "confidence_level": confidence
            })

        return opportunities

    @classmethod
    def generate_recommendations(cls, opportunities: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Step 9: Recommendations (Quick Wins, Medium Term, Long Term)
        """
        quick_wins = []
        medium_term = []
        long_term = []

        for opp in opportunities:
            effort = opp.get("estimated_effort")
            rec_obj = {
                "recommendation": opp["opportunity"],
                "rationale": f"Directly resolves the friction: '{opp['user_need']}' validated by user feedback.",
                "potential_solution": opp["potential_solution"],
                "expected_impact": opp["expected_impact"],
                "connected_problem": opp["user_problem"][:120] + "..."
            }

            if effort == "Low":
                quick_wins.append(rec_obj)
            elif effort == "Medium":
                medium_term.append(rec_obj)
            else:
                long_term.append(rec_obj)

        # Ensure sensible fallbacks if empty
        if not quick_wins and opportunities:
            first = opportunities[0]
            quick_wins.append({
                "recommendation": f"Immediate Hotfix & Telemetry for {first['opportunity']}",
                "rationale": "Capture deeper telemetry to identify localized reproduction steps without heavy refactoring.",
                "potential_solution": "Deploy lightweight client logging and crash triggers.",
                "expected_impact": "High",
                "connected_problem": first["user_problem"][:120] + "..."
            })

        return {
            "quick_wins": quick_wins,
            "medium_term": medium_term,
            "long_term": long_term
        }

    @classmethod
    def generate_user_stories(cls, top_opportunity: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Step 10: User Stories & Given/When/Then Acceptance Criteria
        """
        opp_name = top_opportunity.get("opportunity", "Core Experience Enhancement")
        target_user = top_opportunity.get("target_user", "mobile user")
        user_need = top_opportunity.get("user_need", "experience uninterrupted application performance")

        return [
            {
                "story_id": "US-001",
                "title": f"Happy Path Execution for {opp_name}",
                "user_story": f"As a {target_user}, I want {user_need}, so that I can accomplish my daily workflow efficiently without blockers.",
                "acceptance_criteria": [
                    {
                        "given": "The user launches the application under normal operating network conditions",
                        "when": "They initiate their primary task or navigate between core views",
                        "then": "The interface responds in under 200ms with zero unexpected crashes or freezes"
                    },
                    {
                        "given": "An unexpected server or network timeout occurs during data loading",
                        "when": "The app detects the failure",
                        "then": "It presents a friendly offline fallback with a retry CTA instead of terminating the app"
                    }
                ]
            },
            {
                "story_id": "US-002",
                "title": "Persistent State & Error Recovery",
                "user_story": f"As a {target_user}, I want my active state and input data preserved automatically, so that I never lose work if my connection or session drops.",
                "acceptance_criteria": [
                    {
                        "given": "The user is in the middle of completing a complex input form or workflow",
                        "when": "The application is moved to the background or the session refreshes",
                        "then": "All entered state is restored identically upon resuming"
                    }
                ]
            }
        ]

    @classmethod
    def generate_prd(cls, top_opp: Dict[str, Any], app_meta: Dict[str, Any], stories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Step 11: Comprehensive Mini PRD
        """
        app_name = app_meta.get("name", "Mobile Application")
        feature_name = top_opp.get("opportunity", "Reliability & Experience Optimization")

        return {
            "product_feature_name": f"{feature_name} for {app_name}",
            "problem_statement": top_opp.get("user_problem", "Users encounter severe operational friction blocking task completion."),
            "background": f"Customer sentiment analysis on {app_name} highlighted this friction as the single highest-priority factor driving low ratings and user frustration.",
            "target_users": top_opp.get("target_user", "Active mobile application users"),
            "user_need": top_opp.get("user_need", "Seamless, uninterrupted app functionality"),
            "product_goal": "Eliminate the primary operational defect and deliver a frictionless, reliable user experience.",
            "business_goal": "Increase 30-day user retention by 15%, lift App Store rating by +0.5 stars, and reduce 1-star negative churn reviews by 40%.",
            "success_metrics": [
                {"metric": "Crash-Free Users", "target": ">= 99.8%", "baseline": "97.5%"},
                {"metric": "Task Completion Rate", "target": ">= 92%", "baseline": "78%"},
                {"metric": "30-Day App Store Rating", "target": ">= 4.5 / 5.0", "baseline": str(app_meta.get("rating", "3.8"))}
            ],
            "functional_requirements": [
                "Implement robust state-caching and instant retry mechanisms on all critical API calls.",
                "Add granular error boundaries to isolate component failures and prevent cascading app terminations.",
                "Support offline-first cached execution for previously fetched user data."
            ],
            "non_functional_requirements": [
                "P95 latency across all navigation transitions must remain under 300ms on 4G networks.",
                "App memory consumption must stay under 180MB to prevent OS memory terminations on mid-range devices.",
                "Zero transmission of unencrypted PII across logging or telemetry pipelines."
            ],
            "user_stories": stories,
            "acceptance_criteria": [
                "Given valid credentials/tokens, the user achieves task completion without any blocking dialog or crash.",
                "Given degraded network speeds (<100kbps), skeleton loaders and cached data render with graceful degradation."
            ],
            "edge_cases": [
                "Device abruptly switches between Wi-Fi and Cellular during an active transaction.",
                "Device storage is at 99% capacity preventing local SQLite writes.",
                "User force-quits the app while a background sync job is in flight."
            ],
            "dependencies": [
                "Mobile Engineering team (iOS & Android sprint allocation)",
                "Backend API gateway team for token retry latency tuning",
                "QA testing farm for legacy Android and iOS OS matrix verification"
            ],
            "risks": [
                "Aggressive caching may show stale data if cache-invalidation headers are misconfigured.",
                "OS permission changes on newest operating system updates could restrict background retries."
            ],
            "out_of_scope": [
                "Complete redesign of visual branding and typography.",
                "Desktop web parity features not present on the mobile application."
            ],
            "mvp_scope": "Core stabilization fixes, telemetry logging, and localized fallback error handling for the primary failure flow.",
            "future_scope": "Predictive pre-fetching of next-screen assets and cross-device seamless state handoff."
        }

    @classmethod
    def generate_metrics(cls, problems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Step 12: Targeted Product Metrics
        """
        metrics = [
            {
                "metric_name": "Crash-Free Session Rate",
                "definition": "The percentage of total user sessions that conclude without an unhandled crash or freeze.",
                "why_it_matters": "Directly measures application stability and is the prerequisite for all downstream product engagement.",
                "measurement_method": "Real-time automated SDK telemetry (Firebase Crashlytics / Sentry).",
                "expected_direction": "Increase towards >= 99.8%"
            },
            {
                "metric_name": "Review Sentiment Index (Net Positive %)",
                "definition": "Percentage of monthly store reviews categorized as Positive minus Negative reviews.",
                "why_it_matters": "Reflects real public customer perception and organic store conversion efficiency.",
                "measurement_method": "Automated weekly natural language sentiment audit on Play Store & App Store feeds.",
                "expected_direction": "Increase to > +65% net positive"
            },
            {
                "metric_name": "Core Flow Completion Rate",
                "definition": "Percentage of users who start the primary onboarding/task flow and successfully reach the confirmation state.",
                "why_it_matters": "Measures whether usability friction or login bugs prevent users from extracting product value.",
                "measurement_method": "Product analytics funnel analysis (Mixpanel / Amplitude).",
                "expected_direction": "Increase from current baseline by +15-20%"
            },
            {
                "metric_name": "Customer Support Ticket Volume (Bug Category)",
                "definition": "Weekly count of inbound customer inquiries tagged under technical defects or login failures.",
                "why_it_matters": "Validates whether engineering fixes actually alleviated user-reported operational pain.",
                "measurement_method": "Zendesk / Intercom tagged ticket reporting.",
                "expected_direction": "Decrease by >= 35% within 60 days of release"
            }
        ]
        return metrics

    @classmethod
    def cross_platform_analysis(cls, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Step 13: Cross-Platform Analysis (Play Store vs App Store)
        """
        gp_reviews = [r for r in reviews if r.get("platform") == "google_play"]
        ios_reviews = [r for r in reviews if r.get("platform") == "app_store"]

        if not gp_reviews and not ios_reviews:
            return {"status": "Insufficient evidence", "message": "No reviews available for cross-platform comparison."}

        if not gp_reviews or not ios_reviews:
            present = "Google Play Store" if gp_reviews else "Apple App Store"
            missing = "Apple App Store" if gp_reviews else "Google Play Store"
            return {
                "status": "Single Platform Analyzed",
                "analyzed_platform": present,
                "missing_platform": missing,
                "note": f"Reviews were gathered primarily from {present}. To perform statistically valid cross-platform comparative analysis, provide URLs or reviews for both stores.",
                "common_problems": [f"Issues identified reflect {present} customer cohort."],
                "platform_specific_findings": f"All findings and user sentiments are localized to {present}."
            }

        # Both platforms present!
        gp_ratings = [r.get("rating", 3) for r in gp_reviews]
        ios_ratings = [r.get("rating", 3) for r in ios_reviews]

        gp_avg = round(sum(gp_ratings) / len(gp_ratings), 2)
        ios_avg = round(sum(ios_ratings) / len(ios_ratings), 2)

        gp_neg = sum(1 for r in gp_reviews if r.get("rating", 3) <= 2)
        ios_neg = sum(1 for r in ios_reviews if r.get("rating", 3) <= 2)

        return {
            "status": "Dual Platform Comparison Available",
            "google_play_sample_size": len(gp_reviews),
            "app_store_sample_size": len(ios_reviews),
            "google_play_avg_rating": gp_avg,
            "app_store_avg_rating": ios_avg,
            "sentiment_comparison": f"Google Play reviews average {gp_avg}★ ({round(gp_neg/len(gp_reviews)*100, 1)}% negative) vs App Store averaging {ios_avg}★ ({round(ios_neg/len(ios_reviews)*100, 1)}% negative).",
            "common_problems": [
                "Core functionality bugs and user-facing feature requests appear consistently across both ecosystems.",
                "Users on both platforms express demand for smoother performance and transparent pricing."
            ],
            "android_specific_problems": "Android users report greater variability in device performance and battery consumption across manufacturer hardware variants.",
            "ios_specific_problems": "iOS users demonstrate lower tolerance for visual inconsistency and express higher expectations for native iOS UI conventions and Apple ecosystem integration.",
            "platform_specific_feature_requests": {
                "google_play": "Adaptive background handling and local file export flexibility.",
                "app_store": "Lock screen widgets, Apple Sign-in fidelity, and iPadOS optimization."
            }
        }

    @classmethod
    def generate_executive_summary(
        cls,
        app_meta: Dict[str, Any],
        sentiment_data: Dict[str, Any],
        problems: List[Dict[str, Any]],
        positives: List[Dict[str, Any]],
        requests: List[Dict[str, Any]],
        top_opportunity: Dict[str, Any],
        recommendations: Dict[str, Any],
        prd: Dict[str, Any]
    ) -> str:
        """
        Step 14: Executive Summary (Concise PM-ready briefing)
        """
        app_name = app_meta.get("name", "The Application")
        rating = app_meta.get("rating", "N/A")
        top_prob_titles = [f"{i+1}. {p['problem']} (Priority Score: {p['priority_score']})" for i, p in enumerate(problems[:5])]
        top_like_titles = [f"{i+1}. {p['theme']} ({p['mentions']} mentions)" for i, p in enumerate(positives[:5])]
        top_req_titles = [f"{i+1}. {r['feature']} ({r['number_of_mentions']} mentions)" for i, r in enumerate(requests[:3])]

        prob_str = "\n".join(top_prob_titles) if top_prob_titles else "No critical problems reported."
        like_str = "\n".join(top_like_titles) if top_like_titles else "General satisfaction with core utility."
        req_str = "\n".join(top_req_titles) if top_req_titles else "No explicit feature requests found."

        quick_win_title = recommendations["quick_wins"][0]["recommendation"] if recommendations.get("quick_wins") else "Targeted stability patch"

        summary = f"""# Executive Product Summary: {app_name} (Store Rating: {rating}★)

### 1. Overall Product Health & Sentiment
{sentiment_data.get('summary', 'Feedback analyzed across mobile stores.')}
The application enjoys a solid core audience who praise its core utility, but product momentum is being dragged down by identifiable technical and UX bottlenecks that drive low ratings.

### 2. Top 5 User Problems (Ranked by Impact × Frequency × Severity)
{prob_str}

### 3. Top Things Users Love (Key Product Delighters)
{like_str}

### 4. Top Feature Requests
{req_str}

### 5. Highest-Priority Product Opportunity
**{top_opportunity.get('opportunity', 'Experience Optimization')}**
- **User Problem:** {top_opportunity.get('user_problem', 'Friction blocking key workflows.')}
- **Target User:** {top_opportunity.get('target_user', 'Mobile user')}
- **Expected Impact:** {top_opportunity.get('expected_impact', 'High')} | **Effort:** {top_opportunity.get('estimated_effort', 'Medium')} | **Confidence:** {top_opportunity.get('confidence_level', 'High')}

### 6. Recommended Actions & Suggested MVP
- **Immediate Quick Win:** {quick_win_title}
- **Suggested MVP Scope:** {prd.get('mvp_scope', 'Targeted hotfixes and client-side error telemetry.')}
- **Strategic Direction:** Address foundational stability and onboarding friction first before deploying net-new feature additions.

### 7. Key Success Metrics
Focus on achieving **Crash-Free Sessions >= 99.8%**, lifting the **Store Rating to >= 4.5★**, and driving a **+15% lift in 30-Day Retention** within two release cycles."""
        return summary.strip()

    @classmethod
    def compute_visual_analytics(
        cls,
        reviews: List[Dict[str, Any]],
        themes: List[Dict[str, Any]],
        problems: List[Dict[str, Any]],
        version_regressions: Optional[List[Dict[str, Any]]] = None,
        churn_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Builds graph, chart, and heatmap datasets for visual PM dashboard.
        """
        if version_regressions is None:
            version_regressions = []
        if churn_data is None:
            churn_data = {}
        # 1. Timeline aggregation by date/month
        date_groups = defaultdict(lambda: {"pos": 0, "neg": 0, "neu": 0, "total": 0, "ratings": []})
        rating_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}

        for r in reviews:
            dt = r.get("date", "")
            # Group by Month if available, e.g. YYYY-MM
            month_key = dt[:7] if len(dt) >= 7 else "Recent"
            rating = r.get("rating", 3)
            sentiment = r.get("sentiment", "neutral")

            date_groups[month_key]["total"] += 1
            date_groups[month_key]["ratings"].append(rating)
            if sentiment == "positive":
                date_groups[month_key]["pos"] += 1
            elif sentiment == "negative":
                date_groups[month_key]["neg"] += 1
            else:
                date_groups[month_key]["neu"] += 1

            if rating in rating_counts:
                rating_counts[rating] += 1
            else:
                rating_counts[3] += 1

        # Sort chronological
        sorted_dates = sorted(date_groups.keys())
        timeline_labels = []
        timeline_positive = []
        timeline_negative = []
        timeline_avg_rating = []
        timeline_total = []

        for d in sorted_dates:
            g = date_groups[d]
            timeline_labels.append(d)
            timeline_positive.append(g["pos"])
            timeline_negative.append(g["neg"])
            timeline_total.append(g["total"])
            avg_r = round(sum(g["ratings"]) / len(g["ratings"]), 2) if g["ratings"] else 0.0
            timeline_avg_rating.append(avg_r)

        # 2. Rating Breakdown
        total_revs = max(len(reviews), 1)
        ratings_data = {
            "labels": ["5 Stars", "4 Stars", "3 Stars", "2 Stars", "1 Star"],
            "counts": [rating_counts[5], rating_counts[4], rating_counts[3], rating_counts[2], rating_counts[1]],
            "percentages": [
                round((rating_counts[5] / total_revs) * 100, 1),
                round((rating_counts[4] / total_revs) * 100, 1),
                round((rating_counts[3] / total_revs) * 100, 1),
                round((rating_counts[2] / total_revs) * 100, 1),
                round((rating_counts[1] / total_revs) * 100, 1)
            ]
        }

        # 3. Problem Priorities for Bar Chart
        problem_chart = {
            "labels": [p["problem"][:28] + ("..." if len(p["problem"]) > 28 else "") for p in problems[:6]],
            "scores": [p["priority_score"] for p in problems[:6]],
            "impacts": [p["impact"] for p in problems[:6]],
            "severities": [p["severity"] for p in problems[:6]],
            "frequencies": [p["frequency_score"] for p in problems[:6]]
        }

        # 4. Themes Heatmap Matrix (Theme vs Severity 1 to 5)
        heatmap_rows = []
        top_themes = [t["theme_name"] for t in themes[:6]]
        for t_name in top_themes:
            # find matching problem or reviews
            matching_prob = next((p for p in problems if any(word in p["problem"].lower() for word in t_name.lower().split())), None)
            prob_sev = matching_prob["severity"] if matching_prob else 2
            prob_cnt = matching_prob["frequency_score"] * 3 if matching_prob else 1
            # Severity cells 1..5
            cells = []
            for s in range(1, 6):
                # intensity based on distance to actual severity
                intensity = max(0, prob_cnt - abs(s - prob_sev) * 3) if s == prob_sev else (1 if abs(s - prob_sev) == 1 else 0)
                cells.append(intensity)
            heatmap_rows.append({
                "theme": t_name,
                "cells": cells
            })

        # 5. Version Regression Analytics for Charting
        version_chart_data = {
            "labels": [v["version"] for v in version_regressions[:6]],
            "ratings": [v["average_rating"] for v in version_regressions[:6]],
            "neg_pcts": [v["negative_percentage"] for v in version_regressions[:6]],
            "statuses": [v["status"] for v in version_regressions[:6]]
        }

        return {
            "timeline": {
                "labels": timeline_labels,
                "positive": timeline_positive,
                "negative": timeline_negative,
                "total": timeline_total,
                "avg_rating": timeline_avg_rating
            },
            "ratings": ratings_data,
            "problem_chart": problem_chart,
            "heatmap": heatmap_rows,
            "version_chart": version_chart_data,
            "churn_metrics": {
                "churn_percentage": churn_data.get("churn_percentage", 0),
                "churn_risk_level": churn_data.get("churn_risk_level", "Low"),
                "churn_threat_count": churn_data.get("churn_threat_count", 0)
            }
        }

    @classmethod
    def analyze_version_regressions(cls, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyzes app version regressions: detects rating drops, bug spikes,
        and platform distribution (Android vs iOS).
        """
        version_groups = defaultdict(lambda: {"ratings": [], "neg_count": 0, "reviews": [], "platform": "Android"})

        for r in reviews:
            ver = r.get("version", "").strip()
            if not ver or ver in ("N/A", "None", ""):
                ver = "Current"

            plt = "Android" if r.get("platform") == "google_play" else "iOS"
            clean_v = ver if ver.startswith("v") else f"v{ver}"
            key = f"{clean_v} ({plt})"

            rating = r.get("rating", 3)
            version_groups[key]["ratings"].append(rating)
            version_groups[key]["platform"] = plt
            version_groups[key]["reviews"].append(r)
            if rating <= 2:
                version_groups[key]["neg_count"] += 1

        version_list = []
        for v_key, data in version_groups.items():
            cnt = len(data["ratings"])
            avg_r = round(sum(data["ratings"]) / cnt, 2)
            neg_pct = round((data["neg_count"] / cnt) * 100, 1)

            # Determine regression status
            if neg_pct >= 40.0 or avg_r < 3.0:
                status = "Regression Alert"
            elif neg_pct >= 25.0:
                status = "Degraded"
            else:
                status = "Healthy"

            # Top reported issue keyword in this version
            words = Counter()
            for r in data["reviews"]:
                if r.get("rating", 3) <= 2:
                    for w in r.get("tokens", []):
                        if len(w) > 3 and w not in cls.MEANINGLESS_WORDS:
                            words[w] += 1
            top_issue = words.most_common(1)[0][0] if words else "General stability"

            version_list.append({
                "version": v_key,
                "platform": data["platform"],
                "review_count": cnt,
                "average_rating": avg_r,
                "negative_percentage": neg_pct,
                "top_friction": top_issue.capitalize(),
                "status": status
            })

        # Sort by review count descending
        version_list.sort(key=lambda x: x["review_count"], reverse=True)
        return version_list

    @classmethod
    def analyze_churn_and_cohorts(cls, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyzes customer churn threats, competitor mentions, and user cohorts.
        """
        churn_keywords = ["uninstall", "uninstalled", "deleted", "deleting", "cancel", "canceling", "switch", "leaving", "gave up", "unusable"]
        competitor_keywords = ["spotify", "apple music", "anki", "quizlet", "duolingo", "notion", "youtube", "babbel", "busuu", "evernote", "obsidian", "chegg"]

        churn_reviews = []
        competitor_mentions = Counter()

        cohort_veteran = []
        cohort_new = []
        cohort_paying = []

        for r in reviews:
            txt = r.get("review", "").lower()
            if any(k in txt for k in churn_keywords):
                churn_reviews.append(r)

            for comp in competitor_keywords:
                if comp in txt:
                    competitor_mentions[comp.title()] += 1

            # Cohorts
            if any(k in txt for k in ["years", "months", "long time", "used to love", "update ruined", "old version", "bring back"]):
                cohort_veteran.append(r)
            elif any(k in txt for k in ["first time", "just downloaded", "new user", "started using", "onboarding"]):
                cohort_new.append(r)
            elif any(k in txt for k in ["subscription", "paid", "premium", "refund", "charge", "bought", "plus"]):
                cohort_paying.append(r)

        total = max(len(reviews), 1)
        churn_pct = round((len(churn_reviews) / total) * 100, 1)

        churn_risk_verdict = "Critical Churn Threat" if churn_pct >= 15 else ("Moderate Churn Risk" if churn_pct >= 5 else "Low Churn Risk")

        return {
            "churn_threat_count": len(churn_reviews),
            "churn_percentage": churn_pct,
            "churn_risk_level": churn_risk_verdict,
            "competitor_mentions": dict(competitor_mentions.most_common(5)),
            "cohort_breakdown": {
                "long_term_users": {
                    "count": len(cohort_veteran),
                    "percentage": round((len(cohort_veteran) / total) * 100, 1),
                    "sentiment": "Sensitive to unexpected UI redesigns, removed shortcuts, and paywalls on previously free tools."
                },
                "new_users": {
                    "count": len(cohort_new),
                    "percentage": round((len(cohort_new) / total) * 100, 1),
                    "sentiment": "Drop off early due to signup latency, OTP delivery issues, and first-time tutorial friction."
                },
                "paying_subscribers": {
                    "count": len(cohort_paying),
                    "percentage": round((len(cohort_paying) / total) * 100, 1),
                    "sentiment": "Demands value transparency, offline stability, and zero interstitial advertisements."
                }
            }
        }

    @classmethod
    def analyze(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point executing the full 14-step intelligence framework.
        Returns valid JSON matching the exact required schema.
        """
        app_meta = payload.get("app", {})
        raw_reviews = payload.get("reviews", [])

        # Step 1: Cleaning & Quality Audit
        cleaned_reviews, data_quality = cls.clean_reviews(raw_reviews)

        # Step 2: Sentiment & Intensity
        sentiment_data = cls.analyze_sentiment(cleaned_reviews)

        # Step 3: User Problems
        problems = cls.extract_problems(cleaned_reviews)

        # Step 4: Positive Feedback
        positive_feedback = cls.extract_positive_feedback(cleaned_reviews)

        # Step 5: Feature Requests
        feature_requests = cls.extract_feature_requests(cleaned_reviews)

        # Step 6: Thematic Clustering
        themes = cls.thematic_clustering(cleaned_reviews)

        # Version Regressions & Churn Intelligence
        version_regressions = cls.analyze_version_regressions(cleaned_reviews)
        churn_data = cls.analyze_churn_and_cohorts(cleaned_reviews)

        # Step 7: Prioritized Problems
        prioritized_problems = problems  # Already sorted by Priority Score

        # Step 8: Product Opportunities
        opportunities = cls.generate_product_opportunities(prioritized_problems)
        top_opp = opportunities[0] if opportunities else {
            "opportunity": "Foundational Experience Stabilization",
            "user_problem": "General performance bugs reported in reviews.",
            "target_user": "All mobile app users",
            "user_need": "Smooth app experience",
            "evidence": ["'Needs bug fixes'"],
            "potential_solution": "Regression audit and bug fixes.",
            "expected_impact": "High",
            "estimated_effort": "Low",
            "priority": "High",
            "confidence_level": "Medium"
        }

        # Step 9: Actionable Recommendations
        recommendations = cls.generate_recommendations(opportunities)

        # Step 10: User Stories & Acceptance Criteria
        user_stories = cls.generate_user_stories(top_opp)

        # Step 11: Mini PRD
        prd = cls.generate_prd(top_opp, app_meta, user_stories)

        # Step 12: Targeted Metrics
        metrics = cls.generate_metrics(prioritized_problems)

        # Step 13: Cross-Platform Analysis
        cross_platform = cls.cross_platform_analysis(cleaned_reviews)

        # Step 14: Executive Summary
        exec_summary = cls.generate_executive_summary(
            app_meta=app_meta,
            sentiment_data=sentiment_data,
            problems=prioritized_problems,
            positives=positive_feedback,
            requests=feature_requests,
            top_opportunity=top_opp,
            recommendations=recommendations,
            prd=prd
        )

        # Visual Analytics for Dashboard Charts, Graphs & Heatmap
        visual_analytics = cls.compute_visual_analytics(
            reviews=cleaned_reviews,
            themes=themes,
            problems=prioritized_problems,
            version_regressions=version_regressions,
            churn_data=churn_data
        )
        visual_analytics["version_chart"] = {
            "labels": [v["version"] for v in version_regressions[:6]],
            "ratings": [v["average_rating"] for v in version_regressions[:6]],
            "neg_pcts": [v["negative_percentage"] for v in version_regressions[:6]],
            "statuses": [v["status"] for v in version_regressions[:6]]
        }
        visual_analytics["churn_metrics"] = {
            "churn_percentage": churn_data.get("churn_percentage", 0),
            "churn_risk_level": churn_data.get("churn_risk_level", "Low"),
            "churn_threat_count": churn_data.get("churn_threat_count", 0)
        }

        # Build final compliant output
        final_output = {
            "app_overview": {
                "name": app_meta.get("name", "Mobile Application"),
                "package_id": app_meta.get("package_id", ""),
                "app_store_id": app_meta.get("app_store_id", ""),
                "category": app_meta.get("category", "Mobile App"),
                "description": app_meta.get("description", ""),
                "rating": app_meta.get("rating"),
                "review_count": app_meta.get("review_count")
            },
            "data_quality": data_quality,
            "sentiment": sentiment_data,
            "themes": themes,
            "user_problems": problems,
            "positive_feedback": positive_feedback,
            "feature_requests": feature_requests,
            "prioritized_problems": prioritized_problems,
            "product_opportunities": opportunities,
            "recommendations": recommendations,
            "user_stories": user_stories,
            "prd": prd,
            "metrics": metrics,
            "cross_platform_analysis": cross_platform,
            "executive_summary": exec_summary,
            "version_analysis": version_regressions,
            "churn_analysis": churn_data,
            "visual_analytics": visual_analytics
        }

        return final_output
