import cProfile
import timeit

import approach1
import approach2

if __name__ == '__main__':
    n = 100
    print('\n------------RUNNING APPROACH 1------------')
    print('\nILLUSTRATIONS-----------------------------')
    code = "approach1.illustrate('M','NS',35,100000,1255.03)"
    t = timeit.Timer(code, setup='import approach1')
    print(f"{n} calls:", t.timeit(number=n))
    print(f"{n} calls, 5 repeats:", t.repeat(number=n))
    cProfile.run(code, sort='tottime')

    print('\nSOLVES------------------------------------')
    code = "approach1.solve_for_premium('M','NS',35,100000)"
    t = timeit.Timer(code, setup='import approach1')
    print(f"{n} calls:", t.timeit(number=n))
    print(f"{n} calls, 5 repeats:", t.repeat(number=n))

    print('\n------------RUNNING APPROACH 2------------')
    print('\nILLUSTRATIONS-----------------------------')
    code = 'ins = approach2.Insured("M", "NS", 35)\n'
    code += 'prod = approach2.Product1\n'
    code += 'pol = approach2.UniversalLifePolicy(ins, prod, 100000)\n'
    code += 'pol.at_issue_illustration(1255.03)'
    t = timeit.Timer(code, setup='import approach2')
    print(f"{n} calls:", t.timeit(number=n))
    print(f"{n} calls, 5 repeats:", t.repeat(number=n))
    cProfile.run(code, sort='tottime')

    print('\nSOLVES------------------------------------')
    code = 'ins = approach2.Insured("M", "NS", 35)\n'
    code += 'prod = approach2.Product1\n'
    code += 'pol = approach2.UniversalLifePolicy(ins, prod, 100000)\n'
    code += 'pol.solve_minimum_premium_to_maturity()'
    t = timeit.Timer(code, setup='import approach2')
    print(f"{n} calls:", t.timeit(number=n))
    print(f"{n} calls, 5 repeats:", t.repeat(number=n))
    cProfile.run(code, sort='tottime')