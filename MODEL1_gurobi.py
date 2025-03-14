from gurobipy import Model, GRB, quicksum
import numpy as np
import time

# Parameters
minB, maxB = 10, 15    # Range for number of bars
minO, maxO = 3, 5      # Range for number of orders
MaxLength = 10         # Maximum bar length
W = 45                 # Reusability lower limit
CC = 400               # Cost of a cut
CW = 100                # Unit cost of waste
BIGM = 1000             # Large constant for Big-M constraints
num_runs = 1            # Number of simulations to run
#MODEL1
epsilon = 1e-3


def generate_random_data():
    #np.random.seed(30)
    n = np.random.randint(minB, maxB)               # Number of bars
    m = np.random.randint(minO, maxO)               # Number of orders
    l = np.random.randint(W, MaxLength, size=n)     # Stock lengths (n long vector)
    r = np.random.randint(1, MaxLength, size=m)     # Order lengths (m long vector)
    return n, m, l, r


def m1_run_cutting_stock_optimizer(run_id):
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
    n = 10
    m = 6
    l = [107, 195, 280, 163, 230, 55, 218, 290, 97, 151]
    r = [ 70, 44, 69, 222, 250, 31]
# =============================================================================
#     n = 6
#     m = 9
#     l = [200, 200, 200, 150, 150, 150]
#     r = [100, 80, 70, 70, 70, 60, 60, 50, 50]
# =============================================================================

    model = Model(f"1D_Cutting_Stock_Run_{run_id}")
    
    # Variables
    X = model.addVars(m, n, vtype=GRB.BINARY, name="X")                 # Assignment matrix
    LOl = model.addVars(n, vtype=GRB.CONTINUOUS, lb=0, name="LOl")      # Leftover length
    YR = model.addVars(n, vtype=GRB.BINARY, name="YR")                  # Reusable leftover indicator
    WL = model.addVars(n, vtype=GRB.CONTINUOUS, lb=0, name="WL")        # Waste length
   
    # MODEL1 extra variables
    z = model.addVars(n, vtype=GRB.BINARY, name="z")                              
    YLR = model.addVars(n, vtype=GRB.BINARY, name="YLR")                # 1 if lefotver returns to stock


    # OBJECTIVE FUNCTION - minimize total waste length
    model.setObjective(quicksum(WL[j] for j in range(n)), GRB.MINIMIZE)

    # CONSTRAINTS:
    # 1 Ensures that each object’s length is completely allocated to item cuts or leftover stock
    for j in range(n):
        model.addConstr(quicksum(X[i, j] * r[i] for i in range(m)) + LOl[j] == l[j])
    
    # 2 Ensures that all ordered items are cut in the required quantities
    for i in range(m):
        model.addConstr(quicksum(X[i, j] for j in range(n)) == 1)
        
    # 3 If any items are cut from an object, the binary z_j is set to 1
    for j in range(n):
        model.addConstr(z[j] <= quicksum(X[i, j] for j in range(n)))
    
    # 4 Ensures z_j is 1 only if items are cut
    for j in range(n):
        model.addConstr(BIGM * z[j] >= quicksum(X[i, j] for j in range(n)))
        
    # 5 If the leftover is smaller than W, it can not be reused (YR_j = 0)
    for j in range(n):
        model.addConstr((LOl[j] -  W) >= -BIGM * (1 - YR[j]) +  epsilon)
    
    # 6 Ensures consistency in defining waste
    for j in range(n):
        model.addConstr((LOl[j] -  W) <=  BIGM * (YR[j]))
        
    # 7 If waste exists (YR_j = 0), it contributes to WL_j
    for j in range(n):
        model.addConstr(WL[j] -  BIGM * (1 - YR[j]) <= 0)
        
    # 8 Ensures that waste is only counted when z_j = 1
    for j in range(n):
        model.addConstr(WL[j] -  BIGM * z[j] <= 0)
        
    # 9 Waste cannot exceed the leftover amount
    for j in range(n):
        model.addConstr(-LOl[j] + WL[j] <= 0)
    
    # 10 Ensures correct handling of waste
    for j in range(n):
        model.addConstr(LOl[j] - WL[j] +  BIGM * (1 - YR[j]) + BIGM * z[j] 
                        <= 2 * BIGM)
        
    # 11 Ensures that an object can only become retail if it was actually used
    for j in range(n):
        model.addConstr(-z[j] + YLR[j] <= 0)
    
    # 12 An object cannot be both waste and retail
    for j in range(n):
        model.addConstr((1 - YR[j]) + YLR[j] <= 1)
        
    # 13 Ensures mutual exclusivity between waste, retail, and object usage
    for j in range(n):
        model.addConstr(z[j] - (1 - YR[j]) - YLR[j] <= 0)
    
    # 14 At most one object can become retail
    for j in range(n):
        model.addConstr(YLR[j] <= 1)
    

    # Solve model
    start_time = time.time()
    model.setParam('OutputFlag', 0)  # Disable(0) / enable(1) detailed solver output
    model.optimize()
    elapsed_time = time.time() - start_time

    # Display results
    if model.status == GRB.OPTIMAL:
        print(f"\n🟢 Run {run_id}: Optimal Objective Value: {model.ObjVal}")
        CutCount = sum(sum(X[i, j].X for i in range(m)) - 1 
        + (1 if l[j] > sum(X[i, j].X * r[i] for i in range(m)) else 0)for j in range(n))
        
        CutCost = CC * CutCount      
        
        waste = sum(WL[j].X for j in range(n))
        
        UsedBars = sum(1 for j in range(n) if sum(X[i, j].X for i in range(m)) > 0)
        
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
    m1_run_cutting_stock_optimizer(run)
