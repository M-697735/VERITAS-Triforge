import os
import sys

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.main import run_analysis_pipeline, SAMPLE_DIR, SAMPLES_META

def verify_all_samples():
    print("=" * 70)
    print("VERITAS EMAIL FORENSICS ENGINE — AUTOMATED VERIFICATION SUITE")
    print("=" * 70)
    
    expected_results = {
        "sample-1": {"verdict": "Likely Legitimate", "count": 0, "rules": []},
        "sample-2": {"verdict": "Likely Fraudulent", "count": 2, "rules": ["C1", "C5"]},
        "sample-3": {"verdict": "Likely Fraudulent", "count": 3, "rules": ["C1", "C2", "C5"]},
        "sample-4": {"verdict": "Likely Fraudulent", "count": 2, "rules": ["C4", "C5"]},
        "sample-5": {"verdict": "Needs Review", "count": 1, "rules": ["C6"]},
    }
    
    all_passed = True
    
    for sample in SAMPLES_META:
        sample_id = sample["id"]
        filename = sample["filename"]
        file_path = os.path.join(SAMPLE_DIR, filename)
        
        if not os.path.exists(file_path):
            print(f"[FAIL] Missing file: {filename}")
            all_passed = False
            continue
            
        with open(file_path, "rb") as f:
            raw_bytes = f.read()
            
        res = run_analysis_pipeline(raw_bytes, filename=filename)
        
        verdict = res["verdict"]["verdict"]
        contradictions = res["contradictions"]
        fired_rules = [c["rule_id"] for c in contradictions]
        fired_count = len(fired_rules)
        
        exp = expected_results[sample_id]
        
        verdict_ok = (verdict == exp["verdict"])
        count_ok = (fired_count == exp["count"])
        rules_ok = (sorted(fired_rules) == sorted(exp["rules"]))
        
        status = "PASSED [OK]" if (verdict_ok and count_ok and rules_ok) else "FAILED [FAIL]"
        if not (verdict_ok and count_ok and rules_ok):
            all_passed = False
            
        print(f"\n{sample['name']}:")
        print(f"  File: {filename}")
        print(f"  Result: {status}")
        print(f"  Verdict: {verdict} (Expected: {exp['verdict']})")
        print(f"  Contradiction Count: {fired_count} (Expected: {exp['count']})")
        print(f"  Fired Rule IDs: {fired_rules} (Expected: {exp['rules']})")
        
        if not rules_ok:
            print("  [DETAILS] Contradiction Details:")
            for c in contradictions:
                print(f"    - [{c['rule_id']}] {c['title']}: {c['description']}")
                
    print("\n" + "=" * 70)
    if all_passed:
        print("ALL 5 SAMPLE VERIFICATION TESTS PASSED PERFECTLY (100% MATCH)!")
    else:
        print("SOME VERIFICATION TESTS FAILED — ATTENTION REQUIRED!")
    print("=" * 70)
    
    return all_passed

if __name__ == "__main__":
    success = verify_all_samples()
    sys.exit(0 if success else 1)
