from gurobipy import Model, GRB, quicksum
import time


def run_cso_m3(params, n, m, l, r, run_id):
    model = Model(f"Model3_Run_{run_id}")
    
    # Variables
    X = model.addVars(m, n, vtype=GRB.BINARY, name="X")                 # Assignment matrix
    LOl = model.addVars(n, vtype=GRB.CONTINUOUS, lb=0, name="LOl")      # Leftover length
    WL = model.addVars(n, vtype=GRB.CONTINUOUS, lb=0, name="WL")        # Waste length
    YU = model.addVars(n, vtype=GRB.BINARY, name="YU")                  # Used bar indicator
    
    #MODEL3 extra variable              
    YLR = model.addVars(n, vtype=GRB.BINARY, name="YLR")                # 1 if leftover returns to stock


    # OBJECTIVE FUNCTION - Minimize cost of waste and cost of retained retail
    model.setObjective(quicksum(WL[j] * params['CW'] + YLR[j] * params['CR'] for j in range(n)), GRB.MINIMIZE)

    # CONSTRAINTS:
    # 1 Ensures object length is either used or stored as leftover
    for j in range(n):
        model.addConstr(quicksum(X[i, j] * r[i] for i in range(m)) + LOl[j] == l[j] * YU[j])
    
    # 2 Guarantees all ordered items are cut
    for i in range(m):
        model.addConstr(quicksum(X[i, j] for j in range(n)) == 1)
        
    # 3 Ensures leftover is large enough to be retail if classified as such
    for j in range(n):
        model.addConstr(params['W'] - LOl[j] + params['W'] * (YLR[j] - 1) <= 0)
    
    # 4 Limits waste and retail classification
    for j in range(n):
        model.addConstr(LOl[j] - WL[j] - (YLR[j] + (1 - YU[j])) * max(l) <= 0)
        
    
    start_time = time.time()
    model.setParam('OutputFlag', 0)  # Disable(0) / enable(1) detailed solver output
    model.optimize()
    elapsed_time = time.time() - start_time
    

    if model.status == GRB.OPTIMAL:
        cuts = sum(sum(X[i, j].X for i in range(m)) - 1 
        + (1 if l[j] > sum(X[i, j].X * r[i] for i in range(m)) else 0)for j in range(n))
        
        used_bars = sum(YU[j].X for j in range(n))
        
        #used_bars2 = sum(1 for j in range(n) if sum(X[i, j].X for i in range(m)) > 0)
        
        waste =sum(WL[j].X for j in range(n))
        
        return {
            'run': run_id,
            'model': 'model3',
            'cuts': cuts,
            'cuts_cost': cuts * params['CC'],
            'waste': waste,
            'waste_cost': waste * params['CW'],
            'used_bars': used_bars,
            'total_cost': cuts * params['CC'] + waste * params['CW'],
            'solve_time': elapsed_time
            }
    else:
        return {
            'run': run_id, 
            'model': 'model3',
            'status': 'infeasible'
            }
