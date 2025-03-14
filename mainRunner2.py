import numpy as np
import pandas as pd
from mo import run_cso_mo
from m1 import run_cso_m1
from m2 import run_cso_m2
from m3 import run_cso_m3

params = {
    'minB': 9, 'maxB': 11,          # Min and max number of bars
    'minO': 5, 'maxO': 10,          # Min and max number of orderstask
    'MaxBarLength': 300,            # Max length of bars
    'W': 45,                        # Waste limit length
    'CC': 400,                      # Cost of a cut
    'CW': 100,                      # Unit cost of waste
    'CR': 200,                      # Cost of returning a reusable leftover to stock
    'BIGM': 1000,
    'epsilon': 1e-3
}

def generate_random_data(params):
    n = np.random.randint(params['minB'], params['maxB'])               # Number of bars
    m = np.random.randint(params['minO'], params['maxO'])               # Number of orders
    l = np.random.randint(params['W'], params['MaxBarLength'], size=n)  # Stock lengths
    r = np.random.randint(1, params['MaxBarLength'], size=m)            # Order lengths
    return n, m, l, r

results = []
successful_runs = 0
failed_attempts = 0

num_runs = 100                      # Number of successful runs required

while successful_runs < num_runs:
    run_id = successful_runs + 1
    n, m, l, r = generate_random_data(params)
    successful_run = False
    
    for model_func in [run_cso_mo, run_cso_m1, run_cso_m2, run_cso_m3]:
        try:
            result = model_func(params, n, m, l, r, run_id)
            if result.get('status') == 'infeasible':
                failed_attempts += 1        # Count infeasible runs as failed
                continue                    # Skip storing infeasible runs
            
            results.append(result)          # Successful run gets stored in results
            successful_run = True
        except Exception:
            failed_attempts += 1            # Count other failures
            continue                        # Ignore failed runs
    
    if successful_run:
        successful_runs += 1                # Only count successful runs
        print(successful_runs, end=", ")    # Prints successful run IDs to console
        results.append({                    # Separating line between runs
            'run': "----------",
            'bars': "----------",
            'orders': "----------",
            'model': "----------",
            'cuts': "----------",
            'cust_cost': "----------",
            'waste': "----------",
            'waste_cost': "----------",
            'used_bars': "----------",  
            'total_cost': "----------",
            'solve_time': "----------",
            'bar_lengths': "----------",
            'order_lengths': "----------"
        })


df = pd.DataFrame(results)
df.to_excel("cutting_stock_results.xlsx", index=False)

print()
print(f"Total successful runs: {successful_runs}")
print(f"Total failed attempts (including infeasible): {failed_attempts}")
print(f"Results saved to 'cutting_stock_results.xlsx'")

