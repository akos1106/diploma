from gurobipy import Model, GRB, quicksum
import numpy as np
import time

# Parameters
minB, maxB = 10, 15     # Range for number of bars
minO, maxO = 3, 5     # Range for number of orders
MaxLength = 10         # Maximum bar length
W = 45                 # Reusability lower limit
CC = 400                # Cost of a cut
CW = 100                # Unit cost of waste
BIGM = 1000             # Large constant for Big-M constraints
num_runs = 1            # Number of simulations to run


def generate_random_data():
    n = np.random.randint(minB, maxB)               # Number of bars
    m = np.random.randint(minO, maxO)               # Number of orders
    l = np.random.randint(W, MaxLength, size=n)     # Stock lengths (n long vector)
    r = np.random.randint(1, MaxLength, size=m)     # Order lengths (m long vector)
    return n, m, l, r


def o_run_cutting_stock_optimizer(run_id):
    # Generate new data
# =============================================================================
#     n, m, l, r = generate_random_data()
# =============================================================================
# =============================================================================
#     n = 37
#     m = 4
#     l = [144, 68, 45, 114, 265, 246, 138, 147, 256, 66, 72, 117, 64, 191, 151, 191, 269, 188, 260, 95, 54, 170, 265, 217, 244, 265, 137, 107, 254, 211, 94, 145, 288, 224, 256, 273, 203]
#     r = [93, 21, 120, 263]
# =============================================================================
# =============================================================================
#     n = 15
#     m = 9
#     l = [142, 229, 278, 221, 250, 67, 185, 265, 121, 265, 285, 167, 261, 258, 205]
#     r = [130, 29, 74, 12, 250, 38, 169, 97, 38]
# =============================================================================
    n = 6
    m = 9
    l = [200, 200, 200, 150, 150, 150]
    r = [100, 80, 70, 70, 70, 60, 60, 50, 50]

    model = Model(f"1D_Cutting_Stock_Run_{run_id}")
    
    # Variables
    X = model.addVars(m, n, vtype=GRB.BINARY, name="X")                 # Assignment matrix
    LOl = model.addVars(n, vtype=GRB.CONTINUOUS, lb=0, name="LOl")      # Leftover length
    YL = model.addVars(n, vtype=GRB.BINARY, name="YL")                  # Leftover indicator
    YR = model.addVars(n, vtype=GRB.BINARY, name="YR")                  # Reusable leftover indicator
    WL = model.addVars(n, vtype=GRB.CONTINUOUS, lb=0, name="WL")        # Waste length
    YU = model.addVars(n, vtype=GRB.BINARY, name="YU")                  # Used bar indicator

    # OBJECTIVE FUNCTION - minimize number (cost) of cuts, amount (cost) of waste, and used up bars
    model.setObjective(
        CC * quicksum(quicksum(X[i, j] for i in range(m)) - 1 + YL[j] for j in range(n)) + 
        CW * quicksum(WL[j] for j in range(n)) + 
        quicksum(YU[j] for j in range(n)),
        GRB.MINIMIZE
    )

    # CONSTRAINTS

    # 1. Each order must be assigned exactly once
    for i in range(m):
        model.addConstr(quicksum(X[i, j] for j in range(n)) == 1, name=f"order_assigned_{i}")

    # 2. Bar usage constraint (sum of assigned order lengths + leftover = bar length)
    for j in range(n):
        model.addConstr(quicksum(X[i, j] * r[i] for i in range(m)) + LOl[j] == l[j], name=f"bar_usage_{j}")

    # 3. If a bar has leftover, YL[j] = 1
    for j in range(n):
        model.addConstr(YL[j] >= LOl[j] / l[j], name=f"leftover_binary_{j}")

    # 4. Waste calculation with reusable leftover constraint
    for j in range(n):
        model.addConstr(LOl[j] - WL[j] <= BIGM * YR[j], name=f"waste_relation_1_{j}")
        model.addConstr(W - LOl[j] <= BIGM * (1 - YR[j]), name=f"waste_relation_2_{j}")

    # 5. Object usage condition: if any order is cut from it, it must be marked as used
    for j in range(n):
        model.addConstr(YU[j] >= quicksum(X[i, j] for i in range(m)) / BIGM, name=f"object_usage_{j}")


    # Solve model
    start_time = time.time()
    model.setParam('OutputFlag', 0)  # Disable(0) / enable(1) detailed solver output
    model.optimize()
    elapsed_time = time.time() - start_time

    # Display results
    if model.status == GRB.OPTIMAL:
        print(f"\n🟢 Run {run_id}: Optimal Objective Value: {model.ObjVal}")
        
        CutCount = sum(sum(X[i, j].X for i in range(m)) - 1 + YL[j].X for j in range(n))
        CutCost = CC * CutCount
        waste = sum(WL[j].X for j in range(n))
        UsedBars = sum(YU[j].X for j in range(n))
        
        print(f"      Total cost of cuts: {CutCost} ({int(CutCount)} cuts were made)")
        print(f"      Total waste: {waste} cm and {CW * waste} $.")
        print(f"      Bars used: {int(UsedBars)}")
        print(f"      Total number of orders incoming: {m}")
        print()
        
        print("      CUTTING PLAN:")
        for j in range(n):
            print(f"      Bar {j+1} (Length: {l[j]}, Leftover: {LOl[j].X:.0f}, Waste: {abs(WL[j].X):.0f})")
            for i in range(m):
                if X[i, j].X > 0.5:
                    print(f"       - Order {i+1} (Length: {r[i]})")
            print()

        print(f"   Solution Time: {elapsed_time:.2f} seconds\n")
    else:
        if any(r_i > max(l) for r_i in r):
            print(f"\n🔴 Run {run_id}: Infeasible! \n      Some orders are larger than any stock length!")
            print(f"        Orders: {sorted(int(r_i) for r_i in r)}")
            print(f"        Stock: {sorted(int(l_i) for l_i in l)}") 
            return
        
        elif sum(l) < sum(r):
            print(f"\n🔴 Run {run_id}: Infeasible! \n      Total length of stock is smaller than total length of orders!")
            return
        
        elif model.status == GRB.INFEASIBLE:
            model.computeIIS()
            model.write("infeasible_constraints.ilp")
            print(f"\n🔴 Run {run_id}: Model is infeasible! Check infeasible_constraints.ilp for details.")
        
        elif model.status == GRB.UNBOUNDED:
            print(f"\n🔴 Run {run_id}: Model is unbounded!")
        
        else:
            print(f"\n🔴 Run {run_id}: Model is infeasible or unbounded!")

# Run multiple simulations
for run in range(1, num_runs + 1):
    o_run_cutting_stock_optimizer(run)
