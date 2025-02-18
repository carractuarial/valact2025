import cProfile
import timeit

import approach1
import approach2

if __name__ == '__main__':
    n = 1000
    print('------------RUNNING APPROACH 1------------')
    code = "approach1.illustrate('M','NS',35,100000,1255.03)"
    t = timeit.Timer(code, setup='import approach1; import approach2')
    print(f"{n} calls:", t.timeit(number=n))
    print(f"{n} calls, 5 repeats:", t.repeat(number=n))
    cProfile.run(code, sort='tottime')

    print('------------RUNNING APPROACH 2------------')
    code = 'ins = approach2.Insured("M", "NS", 35)\n'
    code += 'prod = approach2.Product1\n'
    code += 'pol = approach2.Universal_Life_Policy(ins, prod, 100000)\n'
    code += 'pol.at_issue_illustration(1255.03)'
    t = timeit.Timer(code, setup='import approach1; import approach2')
    print(f"{n} calls:", t.timeit(number=n))
    print(f"{n} calls, 5 repeats:", t.repeat(number=n))
    cProfile.run(code, sort='tottime')