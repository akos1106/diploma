from gurobipy import Model, GRB, quicksum
import time


def run_cso_mo(params, n, m, l, r, run_id):
    model = Model(f"OwnModel_Run_{run_id}")
    
    # Variables
    X = model.addVars(m, n, vtype=GRB.BINARY, name="X")                 # Assignment matrix
    LOl = model.addVars(n, vtype=GRB.CONTINUOUS, lb=0, name="LOl")      # Leftover length
    YL = model.addVars(n, vtype=GRB.BINARY, name="YL")                  # Leftover indicator
    YR = model.addVars(n, vtype=GRB.BINARY, name="YR")                  # Reusable leftover indicator
    WL = model.addVars(n, vtype=GRB.CONTINUOUS, lb=0, name="WL")        # Waste length
    YU = model.addVars(n, vtype=GRB.BINARY, name="YU")                  # Used bar indicator

    # OBJECTIVE FUNCTION - minimize number (cost) of cuts, amount (cost) of waste, and used up bars
    model.setObjective(
        params['CC'] * quicksum(quicksum(X[i, j] for i in range(m)) - 1 + YL[j] for j in range(n)) + 
        params['CW'] * quicksum(WL[j] for j in range(n)) + 
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
        model.addConstr(LOl[j] - WL[j] <= params['BIGM'] * YR[j], name=f"waste_relation_1_{j}")
        model.addConstr(params['W'] - LOl[j] <= params['BIGM'] * (1 - YR[j]), name=f"waste_relation_2_{j}")

    # 5. Object usage condition: if any order is cut from it, it must be marked as used
    for j in range(n):
        model.addConstr(YU[j] >= quicksum(X[i, j] for i in range(m)) / params['BIGM'], name=f"object_usage_{j}")


    # Solve model
    start_time = time.time()
    model.setParam('OutputFlag', 0)  # Disable(0) / enable(1) detailed solver output
    model.optimize()
    elapsed_time = time.time() - start_time
    

    if model.status == GRB.OPTIMAL:
        cuts = sum(sum(X[i, j].X for i in range(m)) - 1 + YL[j].X for j in range(n))
        
        #cuts2 = sum(sum(X[i, j].X for i in range(m)) - 1 
        #+ (1 if l[j] > sum(X[i, j].X * r[i] for i in range(m)) else 0)for j in range(n))
        
        used_bars = sum(YU[j].X for j in range(n))
        
        waste = sum(WL[j].X for j in range(n))
        
        return {
            'run': run_id,
            'bars': n,
            'orders': m,
            'model': 'modelO',
            'cuts': cuts,
            'cuts_cost': cuts * params['CC'],
            'waste': waste,
            'waste_cost': waste * params['CW'],
            'used_bars': used_bars,
            'total_cost': cuts * params['CC'] + waste * params['CW'],
            'solve_time': elapsed_time,
            'bar_lengths': l,
            'order_lengths': r
            }
    else:
        return {
            'run': run_id, 
            'model': 'modelO',
            'status': 'infeasible'
            }
