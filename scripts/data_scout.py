import json
import os


def build_rank_windows(user_rank):
    if user_rank <= 2000:
        return {
            "chong_min": user_rank,
            "chong_max": user_rank + 8000,
            "wen_min": user_rank + 8000,
            "wen_max": user_rank + 25000,
            "bao_min": user_rank + 25000,
        }
    return {
        "chong_min": max(1, user_rank - 5000),
        "chong_max": user_rank,
        "wen_min": user_rank,
        "wen_max": user_rank + 15000,
        "bao_min": user_rank + 15000,
    }


class DataScoutAgent:
    def __init__(self, data_path):
        self.data_path = data_path
        with open(data_path, 'r', encoding='utf-8') as f:
            self.db = json.load(f)

    def scout_options(self, user_rank, group='phys', buffer=5000):
        """
        Scout university-major pairs that match the user's rank.
        group: 'phys' or 'hist'
        buffer: Look for schools slightly above rank (for 'Chong') and below (for 'Bao').
        """
        results = {
            "Chong (Aggressive)": [],
            "Wen (Stable)": [],
            "Bao (Guaranteed)": []
        }

        rank_key = f"min_rank_{group}"
        windows = build_rank_windows(user_rank)
        
        for college in self.db['colleges']:
            for major in college['majors']:
                min_rank = major.get(rank_key)
                if min_rank is None:
                    continue
                
                # Logic for Chong/Wen/Bao based on rank
                entry = {
                    "college": college['name'],
                    "major": major['name'],
                    "tier": college['tier'],
                    "min_rank": min_rank,
                    "subject_req": major['subject_req'],
                    "employment_tier": major.get('employment_tier', 'B')
                }

                if min_rank >= windows["chong_min"] and min_rank < windows["chong_max"]:
                    results["Chong (Aggressive)"].append(entry)
                elif min_rank >= windows["wen_min"] and min_rank <= windows["wen_max"]:
                    results["Wen (Stable)"].append(entry)
                elif min_rank > windows["bao_min"]:
                    results["Bao (Guaranteed)"].append(entry)
        
        return results

if __name__ == "__main__":
    # Test for a student ranked 40,000 in Physics group
    scout = DataScoutAgent("e:/Ke_Study/AI_Gaokao_BP_Expert/data/gd_2024_rankings.json")
    matches = scout.scout_options(40000, 'phys')
    
    print("\n" + "="*40)
    print("--- GAOKAO BP SCOUT RESULTS ---")
    print("="*40)
    for category, items in matches.items():
        print(f"\n[{category.upper()}]")
        if not items:
            print("  No options found in this range.")
        for item in items[:5]:
            print(f"  > {item['college']} | {item['major']}")
            print(f"    Rank Req: ~{item['min_rank']} | Market: {item['employment_tier']}")
    print("="*40)
