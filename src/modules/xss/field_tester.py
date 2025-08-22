from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

def eco_verificator(driver, eco_text):
    """Verifica se o texto enviado foi processado corretamente."""
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        body_text = driver.find_element(By.TAG_NAME, "body").text
        if eco_text in body_text:
            return True
        return False
    except Exception as e:
        print(f"An error occurred during verification: {e}")
        return False

def activate_mat_input_field(driver, field_id="mat-input-1"):
    """Ativa especificamente o campo mat-input-1 (barra de pesquisa)"""
    try:
        # Múltiplas estratégias para encontrar o ícone de busca
        search_icon = None
        
        # Estratégia 1: mat-icon com classe mat-search_icon-search 
        try:
            search_icon = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "mat-icon[class*='mat-search_icon-search']"))
            )
        except:
            pass
        
        # Estratégia 2: mat-icon que contém texto "search" 
        if not search_icon:
            try:
                search_icon = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//mat-icon[contains(text(), 'search')]"))
                )
            except:
                pass
        
        # Estratégia 3: qualquer mat-icon na barra superior (toolbar)
        if not search_icon:
            try:
                search_icon = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "mat-toolbar mat-icon"))
                )
            except:
                pass
        
        # Se encontrou, clica e aguarda
        if search_icon:
            search_icon.click()
            time.sleep(1)
            
            # Aguarda o campo ficar ativo
            input_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, field_id))
            )
            
            # Força o foco usando JavaScript
            driver.execute_script("arguments[0].focus();", input_field)
            driver.execute_script("arguments[0].click();", input_field)
            time.sleep(0.5)
            
            return input_field
        else:
            return None
            
    except Exception as e:
        print(f"Erro ao ativar campo {field_id}: {e}")
        return None

def find_field_element(driver, element):
    """Encontra um elemento de campo usando diferentes estratégias"""
    input_field = None
    
    # Tenta encontrar por ID primeiro
    if element['id']:
        try:
            input_field = driver.find_element(By.ID, element['id'])
            input_field.click()
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, element['id'])))
        except:
            input_field = None
    
    # Se não funcionou por ID, tenta por NAME
    if not input_field and element['name']:
        try:
            input_field = driver.find_element(By.NAME, element['name'])
            input_field.click()
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.NAME, element['name'])))
        except:
            input_field = None
    
    return input_field

def submit_form(driver, input_field):
    """Submete o formulário usando diferentes estratégias"""
    try:
        # Procura por submit
        submit_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        submit_button.click()
    except:
        # Procura por login 
        try:
            login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Log in')]")
            login_button.click()
        except:
            input_field.send_keys(Keys.RETURN)

def return_to_original_page(driver, original_url):
    """Volta para a página original e fecha modais"""
    try:
        current_url = driver.current_url
        if current_url != original_url:
            driver.get(original_url)
            
            # Aguarda a página carregar e tenta fechar modais novamente
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)
            
            # Tenta fechar modal que pode aparecer ao voltar
            try:
                close_button = driver.find_element(By.XPATH, "//button[contains(@class, 'close') or contains(@aria-label, 'close') or text()='×']")
                close_button.click()
            except:
                try:
                    dismiss_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Dismiss') or contains(text(), 'OK')]")
                    dismiss_button.click()
                except:
                    try:
                        backdrop = driver.find_element(By.CLASS_NAME, "cdk-overlay-backdrop")
                        backdrop.click()
                    except:
                        try:
                            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        except:
                            pass
    except Exception as e:
        print(f"Erro ao verificar/voltar página: {e}")

def eco_test(lista, driver, test_text):
    """Função de teste para enviar um texto nos campos de input."""
    
    # Salva a URL original para voltar depois de cada teste
    original_url = driver.current_url
    results = []
    
    for element in lista:
        try:
            input_field = None
            # Pula checkboxes e outros tipos não-texto
            if element.get('type') in ['checkbox', 'radio', 'submit', 'button']:
                continue
            
            # Tratamento especial para o campo mat-input-1 (campo de busca)
            if element.get('id') == 'mat-input-1':
                input_field = activate_mat_input_field(driver, 'mat-input-1')
                if not input_field:
                    results.append({
                        'element': element,
                        'status': 'failed',
                        'error': f'Campo de busca mat-input-1 não pode ser ativado'
                    })
                    continue
            else:
                # Tratamento normal para outros campos
                input_field = find_field_element(driver, element)
                    
            if input_field:
                input_field.clear() 
                input_field.send_keys(test_text)

                # Submete o formulário
                submit_form(driver, input_field)
                
                # Aguarda um pouco para a página processar
                time.sleep(2)
                
                # Verifica se mudou de página após o teste
                current_url = driver.current_url
                eco_result = False
                
                if current_url != original_url:
                    eco_result = eco_verificator(driver, test_text)
                else:
                    # Se não mudou, verifica na página atual
                    eco_result = eco_verificator(driver, test_text)
                
                results.append({
                    'element': element,
                    'status': 'success',
                    'payload_sent': test_text,
                    'eco_text': eco_result,
                })
                
        except Exception as e:
            results.append({
                'element': element,
                'status': 'failed',
                'error': str(e)
            })
        
        # Volta para a página original se necessário
        return_to_original_page(driver, original_url)
    
    return results
