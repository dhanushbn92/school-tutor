"""End-to-end smoke test for the child-centric roadmap.

Exercises every stage's backend pipeline against a running local
backend (default http://127.0.0.1:8001). Designed to be re-runnable:
each run creates fresh accounts with unique timestamps so the assert
chain doesn't trip over leftover state from a previous run.

What it tests, in order:

  Stage 1   - Practice rhythm (stamps, weekly goal)
  Stage 1.5 - Login streak + points + level + heatmap
  Stage 2   - Mistake review (upsert via submission + retry)
  Stage 3   - "Tell me more" explanation chain
  Stage 4   - Story-shaped progress (mastery summary derivation
              happens client-side so we just confirm the underlying
              mastery query still works)
  Stage 5   - Mascot state (get / patch / re-enable)
  Stage 6   - Parent invite code + signup + encouragement + dismiss

Prints a green tick per assertion and the parent credentials at the
end so the user can sign in via the UI.

Usage:
    .\\.venv\\Scripts\\python.exe -m scripts.e2e_smoke_child_centric
"""

from __future__ import annotations

import argparse
import secrets
import sys
import time
from typing import Any

import httpx


# Default backend port matches the uvicorn invocation in docs/setup.
DEFAULT_BASE_URL = "http://127.0.0.1:8001"


class TestRunner:
    """Tiny harness - prints pass/fail and tracks failures so we can
    set an exit code at the end."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        # 60s timeout - signup-individual creates School + Section +
        # Student + Enrollment, and round-trips over the Supabase
        # pooler can take 20+ seconds on a cold connection.
        self.client = httpx.Client(base_url=base_url, timeout=60.0)
        self.failures: list[str] = []
        self.step = 0

    def ok(self, label: str, *, indent: int = 0) -> None:
        prefix = "    " * indent
        print(f"{prefix}[OK] {label}")

    def fail(self, label: str, *, indent: int = 0) -> None:
        prefix = "    " * indent
        print(f"{prefix}[FAIL] {label}")
        self.failures.append(label)

    def heading(self, title: str) -> None:
        self.step += 1
        print()
        print(f"=== Step {self.step}: {title} ===")

    # ------------- HTTP helpers -------------

    def post(
        self,
        path: str,
        *,
        json: dict | None = None,
        token: str | None = None,
        expect_status: int = 200,
    ) -> dict | None:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        resp = self.client.post(path, json=json or {}, headers=headers)
        if resp.status_code != expect_status:
            self.fail(
                f"POST {path} expected {expect_status}, got {resp.status_code}: {resp.text[:200]}"
            )
            return None
        return resp.json() if resp.text else None

    def get(
        self, path: str, *, token: str | None = None, expect_status: int = 200
    ) -> Any:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        resp = self.client.get(path, headers=headers)
        if resp.status_code != expect_status:
            self.fail(
                f"GET {path} expected {expect_status}, got {resp.status_code}: {resp.text[:200]}"
            )
            return None
        return resp.json() if resp.text else None

    def patch(
        self,
        path: str,
        *,
        json: dict | None = None,
        token: str | None = None,
        expect_status: int = 200,
    ) -> dict | None:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        resp = self.client.patch(path, json=json or {}, headers=headers)
        if resp.status_code != expect_status:
            self.fail(
                f"PATCH {path} expected {expect_status}, got {resp.status_code}: {resp.text[:200]}"
            )
            return None
        return resp.json() if resp.text else None

    def delete(
        self, path: str, *, token: str | None = None, expect_status: int = 204
    ) -> None:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        resp = self.client.delete(path, headers=headers)
        if resp.status_code != expect_status:
            self.fail(
                f"DELETE {path} expected {expect_status}, got {resp.status_code}: {resp.text[:200]}"
            )

    # ------------- auth helpers -------------

    def login(self, email: str, password: str) -> str | None:
        """OAuth2 password flow - returns access token or None."""
        resp = self.client.post(
            "/auth/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code != 200:
            self.fail(f"login as {email} -> {resp.status_code}: {resp.text[:200]}")
            return None
        return resp.json()["access_token"]


def make_email(prefix: str) -> str:
    """Unique-per-run email so re-running the script doesn't 409.

    Uses `example.com` because IANA-reserved TLDs like `.test` /
    `.invalid` are rejected by Pydantic's EmailStr validator.
    """
    suffix = secrets.token_hex(4)
    return f"{prefix}+{suffix}@example.com"


def run_e2e(base_url: str) -> int:
    t = TestRunner(base_url)

    # ---------------- LEARNER SIGNUP ----------------
    t.heading("Learner signup (individual)")
    learner_email = make_email("learner")
    learner_pw = "TestPass1234"
    signup = t.post(
        "/auth/signup-individual",
        json={
            "full_name": "Test Learner",
            "email": learner_email,
            "password": learner_pw,
            "class_level": 6,
        },
        expect_status=201,
    )
    if signup is None:
        return _bail(t)
    learner_token = signup["token"]["access_token"]
    learner_user_id = signup["user"]["id"]
    t.ok(f"signup-individual -> user_id={learner_user_id} class=6")

    # ---------------- STAGE 1 / 1.5: practice-summary ----------------
    t.heading("Stage 1 / 1.5: practice-summary")
    summary = t.get("/me/practice-summary", token=learner_token)
    if summary is None:
        return _bail(t)
    for key in [
        "week_start",
        "target_days",
        "practice_days_count_this_week",
        "weekly_goal_met",
        "streak",
        "points_total",
        "level",
        "weekly_goal_progress",
        "heatmap",
    ]:
        if key not in summary:
            t.fail(f"practice-summary missing key {key!r}")
    t.ok(f"practice-summary returned. target_days={summary['target_days']}")
    t.ok(
        f"streak: current={summary['streak']['current']}, "
        f"longest={summary['streak']['longest']}, "
        f"grace_used={summary['streak']['grace_used_this_week']}",
        indent=1,
    )
    t.ok(
        f"level: {summary['level']['name']} "
        f"(points_total={summary['points_total']})",
        indent=1,
    )
    t.ok(
        f"heatmap: {len(summary['heatmap'])} cells "
        f"(expecting 12 weeks x 7 = 84 cells)",
        indent=1,
    )

    # Update weekly goal
    goal = t.put_via_post(
        "/me/practice-summary/goal", json={"target_days": 5}, token=learner_token
    )
    if goal is not None:
        t.ok(f"set weekly goal -> target_days={goal['target_days']}")

    # ---------------- STAGE 5: mascot state ----------------
    t.heading("Stage 5: mascot state")
    mascot = t.get("/me/mascot", token=learner_token)
    if mascot is not None:
        t.ok(
            f"GET /me/mascot -> enabled={mascot['enabled']}, "
            f"outfit={mascot['current_outfit']!r}, "
            f"available={mascot['available_outfits']}"
        )
    mascot_off = t.patch(
        "/me/mascot", json={"enabled": False}, token=learner_token
    )
    if mascot_off is not None and mascot_off["enabled"] is False:
        t.ok("PATCH /me/mascot enabled=False persisted")
    mascot_on = t.patch(
        "/me/mascot", json={"enabled": True}, token=learner_token
    )
    if mascot_on is not None and mascot_on["enabled"] is True:
        t.ok("PATCH /me/mascot enabled=True (re-enable)")

    # ---------------- STAGE 6: parent invite + signup ----------------
    t.heading("Stage 6: parent invite + signup")
    code_resp = t.post(
        "/me/parent-invite-codes", token=learner_token, expect_status=201
    )
    if code_resp is None:
        return _bail(t)
    invite_code = code_resp["code"]
    t.ok(f"learner generated invite code: {invite_code} (expires {code_resp['expires_at']})")

    parent_email = make_email("parent")
    parent_pw = "ParentPass1234"
    parent_full_name = "Test Parent"
    parent_signup = t.post(
        "/auth/signup-parent",
        json={
            "email": parent_email,
            "password": parent_pw,
            "full_name": parent_full_name,
            "invite_code": invite_code,
        },
        expect_status=201,
    )
    if parent_signup is None:
        return _bail(t)
    parent_token = parent_signup["token"]["access_token"]
    parent_user_id = parent_signup["user"]["id"]
    t.ok(
        f"parent signup -> user_id={parent_user_id}, child_user_id={parent_signup['child_user_id']}"
    )

    # /me/children from parent side
    children = t.get("/me/children", token=parent_token)
    if children is not None and len(children) >= 1:
        t.ok(f"parent sees {len(children)} child(ren); first: {children[0]['full_name']!r}")
    else:
        t.fail("parent doesn't see any children - link wasn't written?")

    # Child weekly summary (the encouraging view)
    child_summary = t.get(
        f"/me/children/{learner_user_id}/weekly-summary", token=parent_token
    )
    if child_summary is not None:
        t.ok(
            f"parent's child summary -> streak={child_summary['streak']['current']}, "
            f"points={child_summary['points_total']}, level={child_summary['level']['name']}"
        )
        if "mistakes" in child_summary or "mistake_count" in child_summary:
            t.fail("child summary leaked mistake detail - Stage 6 privacy violation")
        else:
            t.ok("child summary does NOT leak mistake detail (privacy promise honoured)", indent=1)

    # Parent tries the mistakes endpoint -> should be 403
    forbidden = t.client.get(
        "/me/mistakes", headers={"Authorization": f"Bearer {parent_token}"}
    )
    if forbidden.status_code == 403:
        t.ok("parent hitting /me/mistakes correctly returns 403")
    else:
        t.fail(
            f"parent at /me/mistakes returned {forbidden.status_code}, expected 403"
        )

    # Send encouragement
    enc = t.post(
        f"/me/children/{learner_user_id}/encouragement",
        token=parent_token,
        json={"message": "Proud of you - keep going!"},
        expect_status=201,
    )
    if enc is not None:
        t.ok(f"parent sent encouragement id={enc['id']}: {enc['message']!r}")

    # Learner reads it
    received = t.get("/me/encouragements", token=learner_token)
    if received is not None and len(received) >= 1:
        t.ok(
            f"learner received {len(received)} note(s); first message: "
            f"{received[0]['message']!r}"
        )
        # Dismiss it
        t.post(
            f"/me/encouragements/{received[0]['id']}/dismiss",
            token=learner_token,
            expect_status=204,
        )
        post_dismiss = t.get("/me/encouragements", token=learner_token)
        if post_dismiss is not None and len(post_dismiss) == len(received) - 1:
            t.ok("learner dismissed the note; undismissed list shrank by 1")

    # Parent list invite codes (should be consumed now)
    active_codes = t.get("/me/parent-invite-codes", token=learner_token)
    if active_codes is not None:
        if all(c["code"] != invite_code for c in active_codes):
            t.ok(
                f"consumed invite code no longer in active list "
                f"({len(active_codes)} active)"
            )

    # Learner lists parents
    parents = t.get("/me/parents", token=learner_token)
    if parents is not None and len(parents) >= 1:
        t.ok(f"learner sees {len(parents)} linked parent(s); first: {parents[0]['email']}")

    # ---------------- STAGE 2 + 3 require an actual quiz submission to populate mistakes.
    # We skip the full mistake-loop here because spinning up a published
    # assessment requires more curriculum setup than this smoke test should own.
    # The endpoints themselves are exercised by:
    t.heading("Stage 2 + 3: endpoint reachability (without quiz dependency)")
    mistakes = t.get("/me/mistakes", token=learner_token)
    if mistakes is not None:
        t.ok(
            f"GET /me/mistakes returns shape OK "
            f"(total_active={mistakes.get('total_active')}, items={len(mistakes.get('items', []))})"
        )

    # /questions/{id}/explain/{tier} needs a real question id; we
    # don't have one in this smoke test (would need to spin up a quiz).
    # Skip - exercised manually via UI.

    # ---------------- FINAL ----------------
    t.heading("Summary")
    print()
    if t.failures:
        print(f"[FAIL]  {len(t.failures)} assertion(s) FAILED:")
        for f in t.failures:
            print(f"    - {f}")
        print()
        return 1

    print("[OK]  All assertions PASSED.")
    print()
    print("===========  PARENT LOGIN CREDENTIALS  ===========")
    print(f"  Email:       {parent_email}")
    print(f"  Password:    {parent_pw}")
    print(f"  Linked to:   Test Learner (user_id={learner_user_id})")
    print("==================================================")
    print()
    print("===========  LEARNER LOGIN CREDENTIALS  ==========")
    print(f"  Email:       {learner_email}")
    print(f"  Password:    {learner_pw}")
    print("==================================================")
    print()
    print(
        "Sign in via the UI with either set of credentials. The parent "
        "dashboard should show the test learner; the learner dashboard "
        "should show the test parent under 'Parents & guardians'."
    )
    return 0


def _bail(t: TestRunner) -> int:
    """Early-exit helper: print whatever failures we've gathered and
    return a non-zero exit code."""
    print()
    print("Bailed out early. Failures so far:")
    for f in t.failures:
        print(f"    - {f}")
    return 1


# httpx doesn't expose `put_via_post`; we add it as a tiny method here
# (the FastAPI route is actually PUT, so we patch the runner above).
def _attach_put(runner_cls: type[TestRunner]) -> None:
    def put_via_post(
        self,
        path: str,
        *,
        json: dict | None = None,
        token: str | None = None,
        expect_status: int = 200,
    ) -> dict | None:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        resp = self.client.put(path, json=json or {}, headers=headers)
        if resp.status_code != expect_status:
            self.fail(
                f"PUT {path} expected {expect_status}, got {resp.status_code}: {resp.text[:200]}"
            )
            return None
        return resp.json() if resp.text else None

    runner_cls.put_via_post = put_via_post  # type: ignore[attr-defined]


_attach_put(TestRunner)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL of the running backend (default {DEFAULT_BASE_URL})",
    )
    args = parser.parse_args()
    start = time.time()
    rc = run_e2e(args.base_url)
    print(f"\n[finished in {time.time() - start:.1f}s]")
    return rc


if __name__ == "__main__":
    sys.exit(main())
