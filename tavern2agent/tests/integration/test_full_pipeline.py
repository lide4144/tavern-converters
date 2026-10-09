import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


def test_full_pipeline():
    card = {
        "data": {
            "name": "艾莉娅",
            "description": "奇幻世界的法师少女。",
            "scenario": "古老图书馆",
            "creator_notes": "风格：水彩。驱动模式：节点驱动，场景切换时触发。",
        }
    }

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        card_path = tmp / "card.json"
        card_path.write_text(json.dumps(card), encoding="utf-8")

        ir_path = tmp / "card-ir.json"
        ui_path = tmp / "ui-semantics.json"
        spec_path = tmp / "page-spec.json"
        web_dir = tmp / "web"

        ir = {
            "version": 1,
            "persona": [{"name": "艾莉娅"}],
            "settingFacts": [],
            "mutableConcepts": [{"name": "mana"}],
            "style": {},
        }
        ir_path.write_text(json.dumps(ir), encoding="utf-8")

        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "extract_ui_semantics.py"), str(card_path), str(ui_path)],
            check=True,
        )
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_page_spec.py"), str(ir_path), str(ui_path), str(spec_path)],
            check=True,
        )
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_page_spec.py"), str(spec_path)],
            check=True,
        )

        sys.path.insert(0, str(ROOT / "scripts"))
        from setup_frontend import setup_frontend

        setup_frontend(str(spec_path), web_dir=str(web_dir))

        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        assert spec["theme"]["base"] == "fantasy"
        assert any(c["type"] == "StatePanel" for c in spec["components"])
        assert (web_dir / "package.json").exists()
        assert (web_dir / "app" / "api" / "state" / "route.ts").exists()
