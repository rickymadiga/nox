import streamlit as st

class Calculator:
    def __init__(self):
        self.history = []

    def add(self, num1, num2):
        result = num1 + num2
        self.history.append(f'{num1} + {num2} = {result}')
        return result

    def subtract(self, num1, num2):
        result = num1 - num2
        self.history.append(f'{num1} - {num2} = {result}')
        return result

    def multiply(self, num1, num2):
        result = num1 * num2
        self.history.append(f'{num1} * {num2} = {result}')
        return result

    def divide(self, num1, num2):
        if num2 == 0:
            return 'Error: Division by zero'
        result = num1 / num2
        self.history.append(f'{num1} / {num2} = {result}')
        return result

    def get_history(self):
        return self.history

def main():
    st.title('Calculator App')
    calc = Calculator()

    col1, col2 = st.columns(2)
    with col1:
        num1 = st.number_input('Number 1')
    with col2:
        num2 = st.number_input('Number 2')

    operation = st.selectbox('Operation', ['Add', 'Subtract', 'Multiply', 'Divide'])

    if st.button('Calculate'):
        if operation == 'Add':
            result = calc.add(num1, num2)
        elif operation == 'Subtract':
            result = calc.subtract(num1, num2)
        elif operation == 'Multiply':
            result = calc.multiply(num1, num2)
        elif operation == 'Divide':
            result = calc.divide(num1, num2)

        st.write(f'Result: {result}')
        st.write('Calculation History:')
        for history in calc.get_history():
            st.write(history)

if __name__ == '__main__':
    main()
