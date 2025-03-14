from gurobipy import Model, GRB, quicksum
import time


def run_cso_m2(params, n, m, l, r, run_id):
    model = Model(f"Model2_Run_{run_id}")
    
    # Variables
    X = model.addVars(m, n, vtype=GRB.BINARY, name="X")                 # Assignment matrix
    WL = model.addVars(n, vtype=GRB.CONTINUOUS, lb=0, name="WL")        # Waste length
   
    #MODEL2 extra variables  
    z = model.addVars(n, vtype=GRB.BINARY, name="z")                           
    YLR = model.addVars(n, vtype=GRB.BINARY, name="YLR")                # 1 if leftover returns to stock


    # OBJECTIVE FUNCTION - minimize total waste length
    model.setObjective(quicksum(WL[j] for j in range(n)), GRB.MINIMIZE)

    # CONSTRAINTS:
    # 1 Items cut cannot exceed object length
    for j in range(n):
        model.addConstr(quicksum(X[i, j] * r[i] for i in range(m)) <= l[j])
    
    # 2 Ensures all ordered items are cut
    for i in range(m):
        model.addConstr(quicksum(X[i, j] for j in range(n)) == 1)
        
    # 3 Retail leftovers must meet the minimum length condition
    for j in range(n):
        model.addConstr(params['W'] * YLR[j] <= l[j] * z[j] - quicksum(X[i, j] * r[i] for i in range(m)))
    
    # 4 Ensures proper classification of waste and retail
    for j in range(n):
        model.addConstr(WL[j] + YLR[j] * params['BIGM'] >= l[j] * z[j] - quicksum(X[i, j] * r[i] for i in range(m)))
        
    # 5 At most one object can be converted to retail
    for j in range(n):
        model.addConstr(YLR[j] <= 1)


    start_time = time.time()
    model.setParam('OutputFlag', 0)  # Disable(0) / enable(1) detailed solver output
    model.optimize()
    elapsed_time = time.time() - start_time
    

    if model.status == GRB.OPTIMAL:
        cuts = sum(sum(X[i, j].X for i in range(m)) - 1 
        + (1 if l[j] > sum(X[i, j].X * r[i] for i in range(m)) else 0)for j in range(n))
        
        used_bars = sum(1 for j in range(n) if sum(X[i, j].X for i in range(m)) > 0)
        
        waste = sum(WL[j].X for j in range(n))
        
        return {
            'run': run_id,
            'model': 'model2',
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
            'model': 'model2',
            'status': 'infeasible'
            }