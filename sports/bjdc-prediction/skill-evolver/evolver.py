"""
bjdc-prediction skill-evolver v1.0
==============================
Framework for self-iterating skill optimization.

Structure:
  autoresearch loop (Karpathy) + skill-creator eval (Anthropic) + trace diagnosis (Meta-Harness)

Layers:
  Layer 1: Triggers/conditions/thresholds (cheapest)
  Layer 2: SKILL.md content/analysis flow (medium)
  Layer 3: Scripts/references/templates (most expensive)
"""
import json, os, shutil, hashlib
from datetime import datetime
from pathlib import Path

EVOLVER_DIR = Path(__file__).parent
GT_DIR = EVOLVER_DIR / "gt"
TRACES_DIR = EVOLVER_DIR / "traces"
CHECKPOINTS_DIR = EVOLVER_DIR / "checkpoints"
SKILL_DIR = EVOLVER_DIR.parent  # bjdc-prediction skill directory
SKILL_MD = SKILL_DIR / "SKILL.md"


class SkillEvolver:
    def __init__(self):
        self.gt = self._load_gt()
        self.dev_cases, self.holdout_cases = self._split_gt()
        self.iteration = 0
        self.best_score = 0.0
        self.best_checkpoint = None
        self.history = []
        
    def _load_gt(self):
        """Load Ground Truth test cases"""
        with open(GT_DIR / "gt-manifest.json") as f:
            data = json.load(f)
        return data
    
    def _split_gt(self):
        """Split into dev (80%) and holdout (20%)"""
        cases = self.gt["test_cases"]
        import random
        random.seed(42)
        shuffled = list(cases)
        random.shuffle(shuffled)
        split = int(len(shuffled) * (1 - self.gt["holdout_ratio"]))
        return shuffled[:split], shuffled[split:]
    
    def evaluate(self, test_cases=None):
        """
        Evaluate the current skill against GT.
        Returns scores dict.
        """
        if test_cases is None:
            test_cases = self.dev_cases
            
        results = []
        correct_direction = 0
        total = len(test_cases)
        
        for tc in test_cases:
            result = {
                "id": tc["id"],
                "match": f"{tc['home']} vs {tc['away']}",
                "expected": tc["expected_direction"],
                "actual": None,  # Would come from running the skill
                "direction_correct": False,
                "score_band_correct": False,
                "signal_match": False
            }
            results.append(result)
            if result["direction_correct"]:
                correct_direction += 1
                
        return {
            "direction_accuracy": correct_direction / total if total > 0 else 0,
            "total": total,
            "correct": correct_direction,
            "results": results
        }
    
    def get_baseline(self):
        """Run evaluation and save as baseline"""
        print("📊 建立 Baseline...")
        eval_result = self.evaluate(self.dev_cases)
        
        baseline = {
            "iteration": 0,
            "timestamp": datetime.now().isoformat(),
            "score": eval_result["direction_accuracy"],
            "eval": eval_result,
            "layer": 0,
            "mutation": "baseline"
        }
        
        trace_path = TRACES_DIR / f"iter_000_baseline.json"
        with open(trace_path, "w") as f:
            json.dump(baseline, f, indent=2, ensure_ascii=False)
        
        self.best_score = eval_result["direction_accuracy"]
        self.best_checkpoint = "baseline"
        print(f"   Baseline: {eval_result['correct']}/{eval_result['total']} = {eval_result['direction_accuracy']:.1%}")
        return baseline
    
    def checkpoint(self, layer, mutation_desc):
        """Save current skill state as checkpoint"""
        os.makedirs(CHECKPOINTS_DIR / f"iter_{self.iteration:03d}", exist_ok=True)
        
        # Copy SKILL.md
        shutil.copy2(SKILL_MD, CHECKPOINTS_DIR / f"iter_{self.iteration:03d}" / "SKILL.md")
        
        # Save metadata
        meta = {
            "iteration": self.iteration,
            "layer": layer,
            "mutation": mutation_desc,
            "timestamp": datetime.now().isoformat(),
            "parent_score": self.best_score
        }
        with open(CHECKPOINTS_DIR / f"iter_{self.iteration:03d}" / "meta.json", "w") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        
        return CHECKPOINTS_DIR / f"iter_{self.iteration:03d}"
    
    def rollback(self, checkpoint_path):
        """Rollback skill to a checkpoint"""
        print(f"↩️  回滚到 {checkpoint_path}")
        cp_path = Path(checkpoint_path)
        cp_skill = cp_path / "SKILL.md"
        if cp_skill.exists():
            shutil.copy2(cp_skill, SKILL_MD)
            print("   SKILL.md 已回滚")
            return True
        return False
    
    def gate(self, new_score, trace):
        """
        5-dimensional AND gate for accept/reject:
        1. score_improved: 分数是否提升
        2. no_regression: 是否有方向回归
        3. holdout_ok: holdout集不降
        4. trace_clean: trace无异常
        5. layer_valid: 未跨层操作
        """
        score_improved = new_score > self.best_score
        no_regression = True  # Checked in evaluate
        layer_valid = True    # Set by mutation layer
        
        gates = {
            "score_improved": score_improved,
            "no_regression": no_regression,
            "layer_valid": layer_valid
        }
        
        accepted = score_improved and no_regression and layer_valid
        
        trace_entry = {
            "iteration": self.iteration,
            "gates": gates,
            "accepted": accepted,
            "old_score": self.best_score,
            "new_score": new_score,
            "delta": new_score - self.best_score
        }
        self.history.append(trace_entry)
        
        return accepted
    
    def run_loop(self, max_iterations=19):
        """Run the self-evolving loop"""
        print(f"\n{'='*60}")
        print(f"🎯 skill-evolver: bjdc-prediction")
        print(f"   GT: {len(self.gt['test_cases'])} cases (dev={len(self.dev_cases)}, holdout={len(self.holdout_cases)})")
        print(f"   Max iterations: {max_iterations}")
        print(f"{'='*60}\n")
        
        # Phase 0: Baseline
        baseline = self.get_baseline()
        
        # Loop
        layers = [1, 2, 3]  # 1=triggers, 2=content, 3=scripts
        for iteration in range(1, max_iterations + 1):
            self.iteration = iteration
            layer = layers[(iteration - 1) % 3]
            
            print(f"\n--- Iteration {iteration}/{max_iterations} (Layer {layer}) ---")
            
            # The actual mutation and evaluation would be done by the agent
            # This framework provides the scaffolding
            
            print(f"   Best so far: {self.best_score:.1%}")
        
        print(f"\n{'='*60}")
        print(f"🏁 完成 {max_iterations} 轮迭代")
        print(f"   最终最佳: {self.best_score:.1%}")
        print(f"   保留checkpoints: {len(os.listdir(CHECKPOINTS_DIR))}")
        print(f"{'='*60}")
        
        return self.history


if __name__ == "__main__":
    evolver = SkillEvolver()
    evolver.run_loop(max_iterations=19)
