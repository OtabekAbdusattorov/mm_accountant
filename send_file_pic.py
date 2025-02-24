import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt, sqlite3
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

db = 'account'


def fetch_all_data_for_admin():
    # Connect to the database
    connection = sqlite3.connect(db)
    cursor = connection.cursor()

    # Query to fetch all requests data
    cursor.execute("SELECT Model, VIN, PlateNumber, Last_Price, VAT, username, issuerID, phoneNumber, date FROM requests")

    # Get all data and column names
    data = cursor.fetchall()
    columns = [description[0] for description in cursor.description]

    # Close the database connection
    connection.close()

    return data, columns


# Function to take a screenshot of all data for admins
def take_screenshot_of_data_for_admin():
    # Fetch all data from the database (admin sees everything)
    data, columns = fetch_all_data_for_admin()

    fig = table_mpl(data, columns)

    # Save the table as an image
    screenshot_path = 'content/admin_data_screenshot.png'  # Fixed name for admin screenshot
    canvas = FigureCanvas(fig)
    canvas.print_figure(screenshot_path, bbox_inches="tight", pad_inches=0.05)

    return [screenshot_path]  # Return the path as a list, can be extended to multiple files



# Function to fetch data from the database for a specific user (based on their last_modify_userID)
def fetch_data_from_database_for_user(user_id):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT Model, VIN, PlateNumber, Last_Price, VAT, username, issuerID, phoneNumber, date FROM requests WHERE issuerID = ?",
        (user_id,)

    )
    data = cursor.fetchall()
    columns = [description[0] for description in cursor.description]
    connection.close()
    return data, columns


# Function to take a screenshot of the data for a specific user
def take_screenshot_of_data_for_user(user_id):
    # Fetch data from the database specific to this user (last_modify_userID)
    data, columns = fetch_data_from_database_for_user(user_id)

    fig = table_mpl(data, columns)

    # Save the table as an image
    screenshot_path = f'content/user_data_screenshot_{user_id}.png'  # Save with user-specific name
    canvas = FigureCanvas(fig)
    canvas.print_figure(screenshot_path, bbox_inches="tight", pad_inches=0.05)

    return [screenshot_path]  # Return the path as a list, can be extended to multiple files


def table_mpl(data, columns):
    if not data:
        return None  # Return None if no data is found

    # Create a matplotlib figure and axis
    fig, ax = plt.subplots(figsize=(len(columns) * 1.5, len(data) * 0.5 + 1), dpi=400)  # Auto-size based on data
    ax.axis('tight')
    ax.axis('off')

    # Create the table
    table_data = [columns] + data  # Add column headers as the first row
    table = ax.table(cellText=table_data,
                     colLabels=None,
                     cellLoc='center',
                     loc='center',
                     colColours=['#f5f5f5'] * len(columns))

    table.auto_set_font_size(False)
    table.set_fontsize(8)  # Adjust font size
    table.auto_set_column_width(col=list(range(len(columns))))

    return fig
