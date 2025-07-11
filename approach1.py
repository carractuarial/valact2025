import polars as pl


def get_per_unit_rates(issue_age: int) -> list[float]:
    """
    Function to retrieve per $1,000 of face amount rates from a CSV
    that varies by issue age and policy year

    Parameters
    ----------
    issue_age: int
        The issue age to retrieve

    Returns
    -------
    list[float]
        List of rates where index 0 is for policy year 1; default entry for
        each index is 0
    """
    rates = [0.0 for _ in range(120)]           # create default array
    df = pl.scan_csv('unit_load.csv').filter(
        pl.col('Issue_Age') == issue_age).collect()  # load filtered csv
    for i in range(len(df)):
        rates[df['Policy_Year'][i]-1] = df['Rate'][i]  # update array
    return rates


def get_coi_rates(gender: str, risk_class: str, issue_age: int) -> list[float]:
    """
    Function to retrieve per $1,000 COI rates from a CSV that varies by 
    gender, risk class, issue age, and policy year

    Parameters
    ----------
    gender: str
        Gender of insured, M or F expected
    risk_class: str
        Risk class of insured, NS or SM expected
    issue_age: int
        Issue age of insured

    Returns
    -------
    list[float]
        List of rates where index 0 is for policy year 1; default entry for
        each index is 0
    """
    rates = [0.0 for _ in range(120)]
    df = pl.scan_csv('coi.csv').filter(pl.col('Issue_Age') == issue_age, pl.col(
        'Gender') == gender, pl.col('Risk_Class') == risk_class).collect()
    for i in range(len(df)):
        rates[df['Policy_Year'][i]-1] = df['Rate'][i]
    return rates


def get_corridor_factors(issue_age: int) -> list[float]:
    """
    Function to retrieve corridor factors from a CSV that varies by attained
    age

    Parameters
    ----------
    issue_age: int
        Issue age of insured

    Returns
    -------
    list[float]
        List of factors by policy year, index 0 is for policy year 1; default values
        of 1 are used if rates not found
    """
    rates = [1.0 for _ in range(120)]
    df = pl.scan_csv('corridor_factors.csv').filter(
        pl.col('Attained_Age') >= issue_age).collect()
    for i in range(len(df)):
        rates[df['Attained_Age'][i]-issue_age] = df['Rate'][i]
    return rates


def get_rates(gender: str, risk_class: str, issue_age: int) -> dict[str, list[float]]:
    """
    Create a dictionary of rates for illustrations

    Parameters
    ----------
    gender: str
        Gender of insured for policy illustration, expected M or F
    risk_class: str
        Risk class of insured for policy illustration, expects NS or SM
    issue_age: int
        Issue age of insured for policy illustration

    Returns
    -------
    dict[str, list[float]]
        A dictionary where keys are strings and values are lists of corresponding rates
        by policy year
    """
    length = 120
    rates = {}
    rates['premium_load'] = [0.06 for _ in range(length)]
    rates['policy_fee'] = [120 for _ in range(length)]
    rates['per_unit'] = get_per_unit_rates(issue_age)
    rates['corridor_factor'] = get_corridor_factors(issue_age)
    rates['naar_disc'] = [1.01**(-1/12) for _ in range(length)]
    rates['coi'] = get_coi_rates(gender, risk_class, issue_age)
    rates['interest'] = [1.03**(1/12) - 1 for _ in range(length)]
    return rates


def illustrate(rates: dict[str, list[float]], issue_age: int, face_amount: int, annual_premium: float) -> dict[str, list[int | float]]:
    """
    Generate an at issue illustration for given case

    Parameters
    ----------
    rates: dict[str, list[float]]
        rates for illustration
    issue_age: int
        Issue age of insured for policy illustration
    face_amount: int
        Face amount for policy illustration
    annual_premium: float
        Annual premium

    Returns
    -------
    dict[str,list[int|float]]
        Illustrated values where keys are columns and resulting values 
        are lists
    """
    maturity_age = 121
    projection_years = maturity_age - issue_age
    fields = ['Policy_Month',
              'Policy_Year',
              'Month_In_Policy_Year',
              'Value_Start',
              'Premium',
              'Premium_Load',
              'Expense_Charge',
              'Death_Benefit',
              'NAAR',
              'COI_Charge',
              'Interest',
              'Value_End']
    output = {field: [0 for _ in range(12*projection_years)]
              for field in fields}

    end_value = 0
    policy_year = 0
    for i in range(12*projection_years):
        policy_year += 1 if (i % 12 == 0) else 0
        start_value = end_value
        premium = annual_premium if (i % 12 == 0) else 0
        premium_load = rates['premium_load'][policy_year-1] * premium
        expense_charge = (
            rates['policy_fee'][policy_year-1] + rates['per_unit'][policy_year-1] * face_amount / 1000) / 12
        av_for_db = start_value + premium - premium_load - expense_charge
        db = max(face_amount, rates['corridor_factor']
                 [policy_year-1] * av_for_db)
        naar = max(0, db * rates['naar_disc']
                   [policy_year-1] - max(0, av_for_db))
        coi = (naar / 1000) * (rates['coi'][policy_year-1] / 12)
        av_for_interest = av_for_db - coi
        interest = max(0, av_for_interest) * rates['interest'][policy_year-1]
        end_value = av_for_interest + interest

        output['Policy_Month'][i] = i+1
        output['Policy_Year'][i] = policy_year
        output['Month_In_Policy_Year'][i] = (i % 12) + 1
        output['Value_Start'][i] = start_value
        output['Premium'][i] = premium
        output['Premium_Load'][i] = premium_load
        output['Expense_Charge'][i] = expense_charge
        output['Death_Benefit'][i] = db
        output['NAAR'][i] = naar
        output['COI_Charge'][i] = coi
        output['Interest'][i] = interest
        output['Value_End'][i] = end_value

        # exit early if lapse before end
        if end_value < 0:
            return output

    # if successful, exit with desired information
    return output


def solve_for_premium(gender: str,
                      risk_class: str,
                      issue_age: int,
                      face_amount: int) -> tuple[float, dict]:
    """
    Determine annual level premium to minimally fund policy to maturity

    Parameters
    ----------
    gender: str
        Gender for insured/case
    risk_class: str
        Risk class for insured/case
    issue_age: int
        Issue age for insured/case
    face_amount: int
        Face amount for policy/case

    Returns
    -------
    tuple[float, dict]
        Tuple whose first item is the solved for premium and second item is the resulting illustration
    """
    guess_lo = 0
    guess_hi = face_amount / 100
    rates = get_rates(gender, risk_class, issue_age)

    while True:
        illus = illustrate(rates, issue_age,
                           face_amount, guess_hi)
        if illus['Value_End'][-1] <= 0:
            guess_lo = guess_hi
            guess_hi = guess_hi * 2
        else:
            break

    while (guess_hi - guess_lo) > 0.005:
        guess_md = (guess_lo + guess_hi)/2
        illus = illustrate(rates, issue_age,
                           face_amount, guess_md)
        if illus['Value_End'][-1] <= 0:
            guess_lo = guess_md
        else:
            guess_hi = guess_md

    result = round(guess_md, 2)
    illus = illustrate(rates, issue_age, face_amount, guess_md)
    if illus['Value_End'][-1] <= 0:
        result += 0.01
        illus = illustrate(rates, issue_age, face_amount, result)

    return (result, illus)


if __name__ == '__main__':
    gender = "M"
    risk_class = "NS"
    issue_age = 35
    face_amount = 100000
    premium = 1255.03
    rates = get_rates(gender, risk_class, issue_age)
    result = illustrate(rates, issue_age, face_amount, premium)
    print(result)
    # gmp, gmf = solve_for_premium(gender, risk_class, issue_age, face_amount)
    # print(gmp)
    # print(gmf)
