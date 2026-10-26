
import time
import random

def run_demo(steps=800, flip_at=400, log_every=50):
    """
    A mock simulation of the imprinter process.
    This is a placeholder for the actual simulation logic.
    """
    print(f"Starting mock imprint simulation...")
    print(f"Total steps: {steps}, Flip at: {flip_at}, Log every: {log_every}")

    entropy = 0.5
    for i in range(steps):
        # Simulate entropy changes
        if i < flip_at:
            entropy -= random.uniform(0.001, 0.01)
        else:
            entropy += random.uniform(0.001, 0.01)
        
        entropy = max(0, min(1, entropy))

        if i % log_every == 0:
            print(f"Step {i}/{steps}... entropy: {entropy:.4f}")
            time.sleep(0.1)
    
    print("Mock imprint simulation finished.")

if __name__ == '__main__':
    run_demo()
