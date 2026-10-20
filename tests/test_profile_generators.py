import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    path = ROOT / ".github" / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fetch_projects = load_script("fetch_projects")
generate_projects = load_script("generate_projects")


class GitHubDataTests(unittest.TestCase):
    def test_github_api_request_uses_bearer_token(self):
        response = io.BytesIO(b'{"ok": true}')
        with patch.object(
            fetch_projects.urllib.request, "urlopen", return_value=response
        ) as urlopen:
            result = fetch_projects.github_json(
                "https://api.github.com/repos/ShashankCodeX/example", "test-token"
            )

        self.assertEqual(result, {"ok": True})
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")

    def test_project_fetch_includes_live_repo_metadata(self):
        project = {
            "name": "Portfolio",
            "repo": "ShashankCodeX/portfolio",
            "description": "My portfolio",
            "tags": ["React"],
        }
        with patch.object(
            fetch_projects,
            "github_json",
            side_effect=[
                {"stargazers_count": 3, "pushed_at": "2026-10-20T10:00:00Z"},
                {"TypeScript": 1200},
            ],
        ):
            result = fetch_projects.fetch(project, "test-token")

        self.assertEqual(result["stars"], 3)
        self.assertEqual(result["languages"], {"TypeScript": 1200})
        self.assertEqual(result["pushed_at"], "2026-10-20T10:00:00Z")

    def test_project_fetch_rejects_invalid_repository_name(self):
        with self.assertRaises(ValueError):
            fetch_projects.fetch({"repo": "https://example.com/not-a-repo"}, "")


class ProjectPanelTests(unittest.TestCase):
    def test_language_bar_uses_byte_percentages(self):
        markup = generate_projects.language_bar(
            {"languages": {"Java": 75, "HTML": 25}},
            100,
            200,
            generate_projects.THEMES["dark"],
        )

        self.assertIn("Java 75%", markup)
        self.assertIn("HTML 25%", markup)

    def test_project_card_escapes_untrusted_text(self):
        project = {
            "name": "<script>Portfolio</script>",
            "repo": "ShashankCodeX/portfolio",
            "description": "A & useful portfolio",
            "tags": ["React & UI"],
            "languages": {"TypeScript": 1},
        }
        markup = generate_projects.card(
            project, 0, 6, 42, generate_projects.THEMES["dark"]
        )

        self.assertIn("&lt;script&gt;Portfolio&lt;/script&gt;", markup)
        self.assertIn("A &amp; useful portfolio", markup)
        self.assertIn("React &amp; UI", markup)
        self.assertNotIn("<script>", markup)

    def test_panel_builds_all_public_projects_for_each_theme(self):
        projects = json.loads((ROOT / "projects.json").read_text(encoding="utf-8"))
        for theme in ("dark", "light"):
            with self.subTest(theme=theme):
                svg = generate_projects.build(projects, theme)
                self.assertIn("SSB Portfolio", svg)
                self.assertIn("Wolf Journal", svg)
                self.assertIn("Hand Gesture Control", svg)
                self.assertEqual(svg.count("PROJECT."), len(projects))
                self.assertIn(generate_projects.THEMES[theme]["background"], svg)

    def test_panel_requires_at_least_one_public_project(self):
        for projects in ([], None):
            with self.subTest(projects=projects):
                with self.assertRaises(ValueError):
                    generate_projects.validate_projects(projects)
        self.assertEqual(generate_projects.validate_projects([{}]), [{}])


if __name__ == "__main__":
    unittest.main()
