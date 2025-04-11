from shiny import App, ui, reactive, render
import pandas as pd
from approach1 import get_rates, solve_for_premium, illustrate

# Define the UI
app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_numeric("issue_age",
                         "Issue Age", 
                         value=35,
                         min=0,
                         max=120),
        ui.input_numeric("face_amount", 
                         "Face Amount", 
                         value=100000, 
                         min=0, 
                         step=1000),
        ui.input_numeric("annual_premium", 
                         "Annual Premium", 
                         value=1255.03, 
                         min=0),
        ui.input_action_button("solve_premium", 
                               "Solve for Premium"),
        ui.input_action_button("generate_illustration", 
                               "Generate Illustration"),
    ),
    ui.card(
        ui.output_table("illustration_table")
    )
)

# Define the server logic
def server(input, output, session):
    
    illustration_df = reactive.value(pd.DataFrame({}))
    
    @reactive.Effect
    @reactive.event(input.solve_premium)
    def _():
        issue_age = input.issue_age()
        face_amount = input.face_amount()
        # Solve for premium (assuming gender and risk_class are fixed for simplicity)
        prem_solve = solve_for_premium("M", "NS", issue_age, face_amount)
        ui.update_numeric("annual_premium", value=prem_solve[0])
        illustration_df.set(pd.DataFrame(prem_solve[1]))

    @reactive.Effect
    @reactive.event(input.generate_illustration)
    def _():
        issue_age = input.issue_age()
        face_amount = input.face_amount()
        annual_premium = input.annual_premium()
        # Get rates and generate illustration
        rates = get_rates("M", "NS", issue_age)
        illustration = illustrate(rates, issue_age, face_amount, annual_premium)
        # Convert the illustration dictionary to a DataFrame for display
        illustration_df.set(pd.DataFrame(illustration))
        
    @output
    @render.table
    def illustration_table():
        return illustration_df()

# Create the app
app = App(app_ui, server)