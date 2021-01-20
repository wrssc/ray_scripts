import wpf
from connect import *
from System.Windows import *
from System.Windows.Controls import *

def open_case( name ):
  "Opens the case having given name."
  
  if name is None or len(name) <= 0:
    raise Exception('No case has been selected.')
  
  case = [c for c in cases if name == c.CaseName]
  if len(case) > 1:
    raise Exception('Name is not giving a unique identification.')
    
  case[0].SetCurrent()
    
class OpenCaseWindow(Window):

  def __init__(self): 
    self.Title = "Open case"
    self.Width = 200
    self.Height = 400
    
    scroll = ScrollViewer()
    scroll.HorizontalAlignment = HorizontalAlignment.Stretch 
    scroll.VerticalAlignment = VerticalAlignment.Stretch 
    scroll.HorizontalScrollBarVisibility = ScrollBarVisibility.Auto
    self.Content = scroll
  
    stack = StackPanel()
    scroll.Content = stack
  
    self.box = ListBox()
    self.box.ItemsSource = [case.CaseName for case in cases]
    stack.Children.Add(self.box)
    
    button = Button()
    button.Width = 50
    button.Margin = Thickness(10)
    button.Content = 'OK'
    button.Click += self.click_ok
    stack.Children.Add(button)
  
  def click_ok(self, sender, args):
    try:
      open_case(self.box.SelectedItem)
    except Exception as error:
      MessageBox.Show('Error: {0}'.format(error))
    else:
      self.Close()
  

if __name__ == "__main__":
  patient = get_current('Patient')
  cases = patient.Cases

  app = Application()
  app.Run(OpenCaseWindow())





