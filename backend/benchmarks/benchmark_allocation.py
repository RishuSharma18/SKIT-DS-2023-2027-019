import time
import random

CATEGORY_FALLBACKS = {
    "TWO_WHEELER": ["TWO_WHEELER", "COMPACT_CAR", "SUV_SEDAN"],
    "COMPACT_CAR": ["COMPACT_CAR", "SUV_SEDAN", "HEAVY_VEHICLE"],
    "SUV_SEDAN": ["SUV_SEDAN", "HEAVY_VEHICLE"],
    "HEAVY_VEHICLE": ["HEAVY_VEHICLE"]
}

class FastSlotAllocator:
    """In-memory benchmark model for high-frequency slot allocations."""

    def __init__(self, slot_count=500):
        self.slots = {}
        cats = ["TWO_WHEELER", "COMPACT_CAR", "SUV_SEDAN", "HEAVY_VEHICLE"]
        for i in range(slot_count):
            s_id = f"S-{i:03d}"
            cat = cats[i % len(cats)]
            self.slots[s_id] = {
                "slot_id": s_id,
                "category": cat,
                "status": "AVAILABLE"
            }

    def allocate(self, requested_category: str):
        fallbacks = CATEGORY_FALLBACKS.get(requested_category, [requested_category])
        for target_cat in fallbacks:
            for s_id, slot in self.slots.items():
                if slot["status"] == "AVAILABLE" and slot["category"] == target_cat:
                    slot["status"] = "RESERVED"
                    return slot
        return None

def run_allocation_benchmark(iterations=5000):
    allocator = FastSlotAllocator(slot_count=1000)
    categories = ["TWO_WHEELER", "COMPACT_CAR", "SUV_SEDAN", "HEAVY_VEHICLE"]
    
    start_time = time.perf_counter()
    success_count = 0
    for _ in range(iterations):
        cat = random.choice(categories)
        res = allocator.allocate(cat)
        if res:
            success_count += 1
            # Release slot periodically to simulate turnover
            if random.random() < 0.8:
                res["status"] = "AVAILABLE"
                
    elapsed = time.perf_counter() - start_time
    rps = iterations / elapsed
    print(f"Benchmark completed: {iterations} allocations in {elapsed:.4f}s ({rps:.0f} req/s)")
    return rps

if __name__ == "__main__":
    run_allocation_benchmark()
