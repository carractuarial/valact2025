/*
Example Rust implementation of approach1.py

Run from command line in parent directory (the one above src which contains this file)
Build: cargo build .
Build with optimizations: cargo build --release .
Run and build if needed: cargo run .
Run and build if needed with optimization: cargo run --release .

*/
use std::{
    error::Error, fs::File, process, collections::HashMap
};

// serde is for serialization and deserialization of data
// using here to simplify reading csv files
use serde::Deserialize;

// need to prepare to deserialize data to structure
#[derive(Deserialize)]
struct IAPYRecord {
    // unfortunately there is not a shortcut here given the nameing used in the csvs
    // there is a quick way to indicate the fields are lowercase, UPPERCASE, PascalCase, 
    // camelCase, snake_case, SCREAMING_SNAKE_CASE, kebab-case, and 
    // SCREAMING-KEBAB-CASE
    #[serde(alias="Issue_Age")]
    issue_age: i8,
    #[serde(alias="Policy_Year")]
    policy_year: i8,
    #[serde(alias="Rate")]
    rate: f64,
}

#[derive(Deserialize)]
struct GenRCIAPYRecord {
    #[serde(alias="Gender")]
    gender: String,
    #[serde(alias="Risk_Class")]
    risk_class: String,
    #[serde(alias="Issue_Age")]
    issue_age: i8,
    #[serde(alias="Policy_Year")]
    policy_year: i8,
    #[serde(alias="Rate")]
    rate: f64,
}

#[derive(Deserialize)]
struct AARecord {
    #[serde(alias="Attained_Age")]
    attained_age: i8,
    #[serde(alias="Rate")]
    rate: f64,
}

fn read_ia_py_csv(path: &str, default: f64, issue_age: i8, ) -> Result<[f64;121], Box<dyn Error>> {
    // create default array
    let mut rates: [f64; 121] = [default; 121];

    let file = File::open(path)?;
    let mut rdr = csv::Reader::from_reader(file);

    for result in rdr.deserialize() {
        let record: IAPYRecord = result?;
        if record.issue_age == issue_age{
            rates[(record.policy_year - 1) as usize] = record.rate
        }
    }
    return Ok(rates);
}

fn read_gen_rc_ia_py_csv(path: &str, default: f64, gender: &str, risk_class: &str, issue_age: i8) -> Result<[f64;121], Box<dyn Error>> {
    let mut rates: [f64;121] = [default;121];

    let file = File::open(path)?;
    let mut rdr = csv::Reader::from_reader(file);

    for result in rdr.deserialize() {
       let record: GenRCIAPYRecord = result?;
       if record.gender == gender && record.risk_class == risk_class && record.issue_age == issue_age {
           rates[(record.policy_year - 1) as usize] = record.rate
       }
    }
    return Ok(rates);
}

fn read_aa_csv(path: &str, default: f64, issue_age: i8) -> Result<[f64;121], Box<dyn Error>> {
    let mut rates: [f64;121] = [default;121];

    let file = File::open(path)?;
    let mut rdr = csv::Reader::from_reader(file);

    for result in rdr.deserialize() {
       let record: AARecord = result?;
       if record.attained_age >= issue_age {
           rates[(record.attained_age - issue_age) as usize] = record.rate;
       }
    }
    return Ok(rates);
}

fn at_issue_projection(rates: HashMap<&'static str, [f64;121]>, issue_age: i8, face_amount: f64, annual_premium: f64) -> Result<f64, Box<dyn Error>> {
    let maturity_age: i8 = 121;
    let projection_years: i8 = maturity_age - issue_age;    
    let mut end_value = 0.0;
    let mut policy_year = 0;

    for i in 0..(12 * i32::from(projection_years)) {
        policy_year += if (i % 12) == 0 {1} else {0};
        let start_value = end_value;
        let premium = if (i % 12) == 0 {annual_premium} else {0.0};
        let premium_load = premium * rates["premium_loads"][policy_year-1];
        let expense_charge = (rates["policy_fees"][policy_year-1] + rates["unit_loads"][policy_year-1] * face_amount / 1000.0) / 12.0;
        let av_for_db = start_value + premium - premium_load - expense_charge;
        let db = face_amount.max(rates["corr_facts"][policy_year-1] * av_for_db);
        let naar = (db * rates["naar_discs"][policy_year-1] - av_for_db.max(0.0)).max(0.0);
        let coi = (naar / 1000.0) * (rates["coi_rates"][policy_year-1] / 12.0);
        let av_for_interest = av_for_db - coi;
        let interest = (av_for_interest * rates["interest_rates"][policy_year - 1]).max(0.0);
        end_value = av_for_interest + interest;
    }
    
    return Ok(end_value);
}

fn solve_for_premium(rates: HashMap<&'static str, [f64;121]>, issue_age: i8, face_amount: f64) -> Result<f64, Box<dyn Error>> {

    let mut guess_lo = 0.0;
    let mut guess_hi = face_amount / 100.0;
    let mut guess_md = 0.0;

    // get rates
    loop {
        let end_value = at_issue_projection(rates.clone(), issue_age, face_amount, guess_hi)?;
        if end_value <= 0.0 {
            guess_lo = guess_hi;
            guess_hi *= 2.0;
        } else {
            break;
        }
    }

    while (guess_hi - guess_lo) > 0.005 {
        guess_md = (guess_lo + guess_hi) / 2.0;
        let end_value = at_issue_projection(rates.clone(), issue_age, face_amount, guess_md)?;
        if end_value <= 0.0 {
            guess_lo = guess_md;
        } else {
            guess_hi = guess_md;
        }
    }

    let mut result = (guess_md * 100.0).round() / 100.0;
    let end_value = at_issue_projection(rates.clone(), issue_age, face_amount, result)?;
    if end_value <= 0.0 {result += 0.01}

    return Ok(result);
}

fn get_rates(gender: &str, risk_class: &str, issue_age: i8) -> Result<HashMap<&'static str, [f64;121]>, Box<dyn Error>> {
    let mut rates: HashMap<&'static str, [f64;121]> = HashMap::new();
    rates.insert("premium_loads", [0.06; 121]);
    rates.insert("policy_fees", [120.0;121]);
    rates.insert("unit_loads", read_ia_py_csv("./data/unit_load.csv", 0.0, issue_age)?);
    rates.insert("corr_facts", read_aa_csv("./data/corridor_factors.csv", 1.0, issue_age)?);
    rates.insert("naar_discs", [f64::powf(1.01, -1.0/12.0);121]);
    rates.insert("coi_rates", read_gen_rc_ia_py_csv("./data/coi.csv", 0.0, gender, risk_class, issue_age)?);
    rates.insert("interest_rates", [f64::powf(1.03,1.0/12.0)-1.0;121]);
    return Ok(rates);
}

fn run() -> Result<(), Box<dyn Error>> {
    use std::time::Instant;
    let mut x = 0.0;
    let now = Instant::now();
    //let rates = get_rates("M", "NS", 35)?;
    for _i in 0..1000 {
        let rates = get_rates("M", "NS", 35)?;
        //x = at_issue_projection(rates, 35, 100000.0, 1255.03)?;
        x = solve_for_premium(rates.clone(), 35, 100000.0)?;
        //println!("{}",_i)
    }
    let elapsed = now.elapsed();
    println!("Premium: {:.2?}", x);
    println!("Elapsed: {:.2?}", elapsed);
    pause();
    Ok(())
}

use std::io;
use std::io::prelude::*;

fn pause() {
    let mut stdin = io::stdin();
    let mut stdout = io::stdout();

    write!(stdout, "Press any key to continue...").unwrap();
    stdout.flush().unwrap();

    let _ = stdin.read(&mut [0u8]).unwrap();
}
fn main() {
    if let Err(err) = run() {
        println!("{}", err);
        process::exit(1);
    }
}
