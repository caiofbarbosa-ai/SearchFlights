"""
Master POC Runner - Execute all Proof of Concept tests
"""

import asyncio
import sys
from datetime import datetime

async def run_google_flights_poc():
    """Run Google Flights POC."""
    print("\n" + "=" * 60)
    print("RUNNING: Google Flights POC")
    print("=" * 60)
    try:
        from google_flights.poc import main as gf_main
        results = await gf_main()
        return "google_flights", results
    except Exception as e:
        print(f"[ERROR] Google Flights POC failed: {e}")
        return "google_flights", [{"status": "ERROR", "error": str(e)}]

async def run_smiles_poc():
    """Run Smiles POC."""
    print("\n" + "=" * 60)
    print("RUNNING: Smiles POC")
    print("=" * 60)
    try:
        from smiles.poc import main as smiles_main
        results = await smiles_main()
        return "smiles", results
    except Exception as e:
        print(f"[ERROR] Smiles POC failed: {e}")
        return "smiles", [{"status": "ERROR", "error": str(e)}]

async def run_azul_poc():
    """Run Azul POC."""
    print("\n" + "=" * 60)
    print("RUNNING: Azul POC")
    print("=" * 60)
    try:
        from azul.poc import main as azul_main
        results = await azul_main()
        return "azul", results
    except Exception as e:
        print(f"[ERROR] Azul POC failed: {e}")
        return "azul", [{"status": "ERROR", "error": str(e)}]

async def main():
    """Execute all POCs sequentially."""
    print("=" * 60)
    print("MASTER POC RUNNER - All Proof of Concept Tests")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    all_results = {}

    # Run each POC
    for name, poc_func in [
        ("Google Flights", run_google_flights_poc),
        ("Smiles", run_smiles_poc),
        ("Azul", run_azul_poc)
    ]:
        key, results = await poc_func()
        all_results[key] = results

        # Brief pause between POCs
        print(f"\nWaiting 5 seconds before next POC...")
        await asyncio.sleep(5)

    # Final Summary
    print("\n" + "=" * 60)
    print("FINAL POC SUMMARY")
    print("=" * 60)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    for source, results in all_results.items():
        success_count = sum(1 for r in results if r.get('status') == 'SUCCESS')
        total_count = len(results)
        status = "✓ PASS" if success_count == total_count and total_count > 0 else "✗ FAIL"
        print(f"{status} {source.upper()}: {success_count}/{total_count} successful")

    # Go/No-Go Decision
    print("\n" + "=" * 60)
    print("GO/NO-GO DECISION")
    print("=" * 60)

    for source, results in all_results.items():
        success_count = sum(1 for r in results if r.get('status') == 'SUCCESS')
        total_count = len(results)
        decision = "GO" if success_count == total_count and total_count > 0 else "NO-GO"
        print(f"{source.upper()}: {decision}")
        if decision == "NO-GO":
            for r in results:
                if r.get('status') != 'SUCCESS':
                    print(f"    - Issue: {r.get('error', 'Unknown')}")

    print("=" * 60)

    return all_results


if __name__ == "__main__":
    # Add poc directory to path
    import sys
    import os
    poc_dir = os.path.dirname(os.path.abspath(__file__))
    if poc_dir not in sys.path:
        sys.path.insert(0, poc_dir)

    asyncio.run(main())
