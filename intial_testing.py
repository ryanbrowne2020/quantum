### DIET PLANNING 

#Hybrid solver

import dimod
from dwave.system import LeapHybridCQMSampler
sampler = LeapHybridCQMSampler()   

'''
The goal of this problem is to optimize the taste of a diet’s foods 
while keeping to the dieter’s budget and daily requirements on 
macro-nutrients.
'''

#formulation (data)
foods = {
  'rice': {'Calories': 100, 'Protein': 3, 'Fat': 1, 'Carbs': 22, 'Fiber': 2,
           'Taste': 7, 'Cost': 2.5, 'Units': 'continuous'},
  'tofu': {'Calories': 140, 'Protein': 17, 'Fat': 9, 'Carbs': 3, 'Fiber': 2,
           'Taste': 2, 'Cost': 4.0, 'Units': 'continuous'},
  'banana': {'Calories': 90, 'Protein': 1, 'Fat': 0, 'Carbs': 23, 'Fiber': 3,
             'Taste': 10, 'Cost': 1.0, 'Units': 'discrete'},
  'lentils': {'Calories': 150, 'Protein': 9, 'Fat': 0, 'Carbs': 25, 'Fiber': 4,
              'Taste': 3, 'Cost': 1.3, 'Units': 'continuous'},
  'bread': {'Calories': 270, 'Protein': 9, 'Fat': 3, 'Carbs': 50, 'Fiber': 3,
            'Taste': 5, 'Cost': 0.25, 'Units': 'continuous'},
  'avocado': {'Calories': 300, 'Protein': 4, 'Fat': 30, 'Carbs': 20, 'Fiber': 14,
              'Taste': 5, 'Cost': 2.0, 'Units': 'discrete'}}

min_nutrients = {"Protein": 50, "Fat": 30, "Carbs": 130, "Fiber": 30}
max_calories = 2000

#variables
quantities = [dimod.Real(f"{food}") if foods[food]["Units"] == "continuous"
                                    else dimod.Integer(f"{food}")
                                    for food in foods.keys()]

print(quantities[0])

#bound setting 
'''
no food by itself should be assigned a quantity that exceeds max_calories.
'''

for ind, food in enumerate(foods.keys()):
  ub = max_calories / foods[food]["Calories"] # upper bound
  quantities[ind].set_upper_bound(food, ub)


#check
print(quantities[0].upper_bound("rice"))
#gives 20.0 as each portion is 100cal

#note: lower bound
'''
Ocean sets a default value of zero for ~dimod.quadratic.Real 
variables, so no explicit configuration is needed in this case.
i.e. the user cannot eat a negative amount of food
'''


## Objective Function 
'''
The objective function must maximize taste of the diet’s foods while minimizing purchase cost

i.e min SUM (qi ci) where q is quantities, c is cost
max SUM (qi ti) where t is taste

To optimize two different objectives, taste and cost, requires weighing one against the other. 
A simple way to do this, is to set priority weights:
objective = alpha(objective_1) + beta(objective_2)
By setting, for example: alpha = 2, beta = 1, 
you double the priority of the first objective compared to the second
'''

#instantiate CQM
cqm = dimod.ConstrainedQuadraticModel()

#utility function: calculate the summations for any given category, such as calories
def total_mix(quantity, category):
  return sum(q * c for q, c in zip(quantity, (foods[food][category] for food in foods.keys())))

'''
Note: for max
because Ocean solvers only minimize objectives, 
to maximize taste, Taste is multiplied by -1 and minimized.
'''

cqm.set_objective(-total_mix(quantities, "Taste") + 6*total_mix(quantities, "Cost"))


## Constraints
# from our min_nutrients and max_calories setting above 

cqm.add_constraint(total_mix(quantities, "Calories") <= max_calories, label="Calories")

for nutrient, amount in min_nutrients.items():
  cqm.add_constraint(total_mix(quantities, nutrient) >= amount, label=nutrient)


## Solve by sampling

sampleset = sampler.sample_cqm(cqm)                    
feasible_sampleset = sampleset.filter(lambda row: row.is_feasible)   
print("{} feasible solutions of {}.".format(len(feasible_sampleset), len(sampleset)))    

'''70 feasible solutions of 117.''' #note varies on the particular execution?

#utility function: print solutions in useful format
def print_diet(sample):
   diet = {food: round(quantity, 1) for food, quantity in sample.items()}
   print(f"Diet: {diet}")
   taste_total = sum(foods[food]["Taste"] * amount for food, amount in sample.items())
   cost_total = sum(foods[food]["Cost"] * amount for food, amount in sample.items())
   print(f"Total taste of {round(taste_total, 2)} at cost {round(cost_total, 2)}")
   for constraint in cqm.iter_constraint_data(sample):
      print(f"{constraint.label} (nominal: {constraint.rhs_energy}): {round(constraint.lhs_energy)}")


#i.e. the best example in this scenario:
best = feasible_sampleset.first.sample                       
print_diet(best)  



## Tuning 
'''
Consider sampling each part of the combined objective on its own (i.e., 
alpha = 1, beta = 0
and alpha = 0, beta = 1
), and comparing the best solutions. Start with taste:
'''
cqm.set_objective(-total_mix(quantities, "Taste"))
sampleset_taste = sampler.sample_cqm(cqm)                     
feasible_sampleset_taste = sampleset_taste.filter(lambda row: row.is_feasible)  
best_taste = feasible_sampleset_taste.first                   
print(round(best_taste.energy)) 
print_diet(best_taste.sample)   