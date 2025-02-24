import abc
from dataclasses import dataclass
import math

import polars as pl

ILLUSTRATION_FIELDS = ['Policy_Month',
                       'Policy_Year',
                       'Month_In_Policy_Year',
                       'Value_Start',
                       'Premium',
                       'Premium_Load',
                       'Expense_Charge',
                       'Value_For_DB',
                       'Death_Benefit',
                       'NAAR',
                       'COI_Charge',
                       'Interest',
                       'Value_End']


@dataclass
class Insured:
    """
    Simple data structure for an insured to house characteristics

    Parameters
    ----------
    gender: str
        Gender of insured
    risk_class: str
        Risk class of insured
    issue_age: int
        Issue age of insured
    """
    gender: str
    risk_class: str
    issue_age: int


class UniversalLifeProduct(abc.ABC):
    """
    Abstract base class for Universal Life products

    Must be subclassed and methods overwritten
    """
    maturity_age = 121

    @staticmethod
    @abc.abstractmethod
    def product_rates_for_policy(insured: Insured) -> dict[str, list[float]]:
        """
        Class method to retrieve product rates for particular insured
        Must be overriden by subclass

        Parameters
        ----------
        insured: Insured
            Insured containing characteristics to retrieve rates for

        Returns
        -------
        dict[str, list[float]]
            Dictionary where keys are product rate types and values are list of rates by policy year
        """
        pass

    @classmethod
    def _new_illustration(cls, issue_age: int) -> dict[str, list[int | float]]:
        return {field: [0 for _ in range(12*(cls.maturity_age - issue_age))] for field in ILLUSTRATION_FIELDS}

    @staticmethod
    def _update_illustration(full: dict[str, list[int | float]], updates: dict[str, int | float], policy_month: int) -> None:
        for key in updates.keys():
            full[key][policy_month-1] = updates[key]

    @staticmethod
    @abc.abstractmethod
    def _monthly_processing(policy_month: int, start_value: float, face_amount: int, annual_premium: float, rates: dict[str, list[float]]) -> dict[str, float | int]:
        """
        Method to execute monthly processing and return necessary information for updates to illustration

        Must be overriden by subclass to contain appropriate processing order

        Parameters
        ----------
        policy_month: int
            policy month to process
        start_value: float
            value at start of policy month
        face_amount: int
            face amount for processing
        annual_premium: float
            annual premium used for processing
        rates: dict[str, list[float]]
            Dictionary of applicable rates

        Returns
        -------
        dict[str, int | float]
            Dictionary whose keys align with full illustration and values are singule integers or floats
        """
        pass

    @classmethod
    def at_issue_illustration(cls, rates: dict[str, list[float]], issue_age: int, face_amount: int, annual_premium: float) -> dict[str, list[int | float]]:
        illustration = cls._new_illustration(issue_age)
        end_value = 0
        for policy_month in range(1, 12*(cls.maturity_age - issue_age)+1):
            monthly_roll = cls._monthly_processing(
                policy_month, end_value, face_amount, annual_premium, rates)
            end_value = monthly_roll['Value_End']
            cls._update_illustration(illustration, monthly_roll, policy_month)

            if end_value < 0:
                # print('WARNING: Policy lapses before maturity')
                return illustration
        return illustration

    @classmethod
    def solve_minimum_premium_to_maturity(cls, rates: dict[str, list[float]], issue_age: int, face_amount: int) -> dict[str, list[int | float]]:
        guess_lo = 0
        guess_hi = face_amount / 100

        while True:
            illustration = cls.at_issue_illustration(
                rates, issue_age, face_amount, guess_hi)
            if illustration['Value_End'][-1] <= 0:
                guess_lo = guess_hi
                guess_hi *= 2
            else:
                break

        while (guess_hi - guess_lo > 0.005):
            guess_md = (guess_lo + guess_hi) / 2
            illustration = cls.at_issue_illustration(
                rates, issue_age, face_amount, guess_md)
            if illustration['Value_End'][-1] <= 0:
                guess_lo = guess_md
            else:
                guess_hi = guess_md

        result = round(guess_md, 2)
        illustration = cls.at_issue_illustration(
            rates, issue_age, face_amount, guess_md)
        if illustration['Value_End'][-1] <= 0:
            result += 0.01

        return result


class Product1(UniversalLifeProduct):
    maturity_age = 121

    @classmethod
    def _get_per_unit_rates(cls, issue_age: int) -> list[float]:
        """
        Retrieve per $1,000 of face amount rates from a CSV
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
        rates = [0.0 for _ in range(
            cls.maturity_age - issue_age)]  # create default array
        df = pl.scan_csv('unit_load.csv').filter(
            pl.col('Issue_Age') == issue_age).collect()  # load filtered csv
        for i in range(len(df)):
            rates[df['Policy_Year'][i]-1] = df['Rate'][i]  # update array
        return rates

    @classmethod
    def _get_coi_rates(cls, gender: str, risk_class: str, issue_age: int) -> list[float]:
        """
        Retrieve per $1,000 COI rates from a CSV that varies by 
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
        rates = [0.0 for _ in range(
            cls.maturity_age - issue_age)]
        df = pl.scan_csv('coi.csv').filter(pl.col('Gender') == gender, pl.col(
            'Risk_Class') == risk_class, pl.col('Issue_Age') == issue_age).collect()
        for i in range(len(df)):
            rates[df['Policy_Year'][i]-1] = df['Rate'][i]
        return rates

    @classmethod
    def _get_corridor_factors(cls, issue_age: int) -> list[float]:
        """
        Retrieve corridor factors from a CSV that varies by attained age

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
        years = cls.maturity_age - issue_age
        rates = [1.0 for _ in range(
            years)]
        df = pl.scan_csv('corridor_factors.csv').filter(
            pl.col('Attained_Age') >= issue_age).collect()
        for i in range(min(years, len(df))):
            rates[df['Attained_Age'][i]-issue_age] = df['Rate'][i]
        return rates

    @classmethod
    def product_rates_for_policy(cls, insured: Insured) -> dict[str, list[float]]:
        years = cls.maturity_age - insured.issue_age
        rates = {}
        rates['premium_loads'] = [0.06 for _ in range(years)]
        rates['policy_fees'] = [120 for _ in range(years)]
        rates['unit_loads'] = cls._get_per_unit_rates(insured.issue_age)

        rates['naar_discount_rates'] = [1.01**(-1/12) for _ in range(years)]
        rates['coi_rates'] = cls._get_coi_rates(
            insured.gender, insured.risk_class, insured.issue_age)
        rates['interest_rates'] = [1.03**(1/12)-1 for _ in range(years)]
        rates['corridor_factors'] = cls._get_corridor_factors(
            insured.issue_age)

        return rates

    @staticmethod
    def _monthly_processing(policy_month, start_value, face_amount, annual_premium, rates):
        # calculate
        policy_year = math.ceil(policy_month/12)
        premium = annual_premium if (policy_month % 12 == 1) else 0
        premium_load = premium * rates['premium_loads'][policy_year-1]
        expense_charge = (rates['policy_fees'][policy_year-1] +
                          rates['unit_loads'][policy_year-1] * face_amount / 1000) / 12
        av_for_db = start_value + premium - premium_load - expense_charge
        db = max(face_amount, av_for_db *
                 rates['corridor_factors'][policy_year-1])
        naar = max(0, db * rates['naar_discount_rates']
                   [policy_year-1] - max(0, av_for_db))
        coi = (naar / 1000) * (rates['coi_rates'][policy_year-1] / 12)
        av_for_interest = av_for_db - coi
        interest = max(0, av_for_interest) * \
            rates['interest_rates'][policy_year-1]
        end_value = av_for_interest + interest

        # prepare output
        output = {'Policy_Month': policy_month,
                  'Policy_Year': policy_year,
                  'Month_In_Policy_Year': (policy_month - 1) % 12 + 1,
                  'Value_Start': start_value,
                  'Premium': premium,
                  'Premium_Load': premium_load,
                  'Expense_Charge': expense_charge,
                  'Value_For_DB': av_for_db,
                  'Death_Benefit': db,
                  'NAAR': naar,
                  'COI_Charge': coi,
                  'Interest': interest,
                  'Value_End': end_value}
        return output


class UniversalLifePolicy:

    def __init__(self, insured: Insured, product: UniversalLifeProduct, face_amount: int):
        self.insured = insured
        self.product = product
        self.face_amount = face_amount
        self.rates = product.product_rates_for_policy(insured)

    @property
    def issue_age(self):
        return self.insured.issue_age

    def at_issue_illustration(self, annual_premium: float):
        return self.product.at_issue_illustration(self.rates, self.issue_age, self.face_amount, annual_premium)

    def solve_minimum_premium_to_maturity(self):
        return self.product.solve_minimum_premium_to_maturity(self.rates, self.issue_age, self.face_amount)


if __name__ == '__main__':
    ins = Insured("M", "NS", 35)
    pol = UniversalLifePolicy(ins, Product1, 100000)
    print(pol.at_issue_illustration(1255.03))
