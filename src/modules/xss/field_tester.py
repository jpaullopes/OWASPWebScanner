from playwright.async_api import TimeoutError as PlaywrightTimeoutError
import asyncio

async def eco_verificator(page, eco_text):
    """Verifica se o texto enviado foi processado corretamente."""
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=10000)
        body_text = await page.locator("body").inner_text()
        if eco_text in body_text:
            return True
        return False
    except Exception as e:
        print(f"An error occurred during verification: {e}")
        return False

async def activate_mat_input_field(page, field_id="mat-input-1"):
    """Ativa especificamente o campo mat-input-1 (barra de pesquisa) usando Playwright"""
    try:
        # Usando o mesmo locator da função activate_search_bar do web_crawler
        search_icon_locator = page.locator("mat-icon[class*='mat-search_icon-search'], mat-icon[data-mat-icon-type='font']")
        
        # Clica no ícone de busca
        await search_icon_locator.first.click(timeout=5000)
        print("Ícone de busca clicado")
        
        # Aguarda o campo de input ficar disponível e editável
        input_field = page.locator(f"#{field_id}")
        await input_field.wait_for(state="visible", timeout=10000)
        await input_field.wait_for(state="editable", timeout=10000)
        
        # Foca no campo
        await input_field.focus()
        await input_field.click()
        await page.wait_for_timeout(500)
        
        return input_field
        
    except PlaywrightTimeoutError:
        print(f"Erro ao ativar campo {field_id}: timeout")
        return None
    except Exception as e:
        print(f"Erro ao ativar campo {field_id}: {e}")
        return None

async def find_field_element(page, element):
    """Encontra um elemento de campo usando diferentes estratégias com Playwright"""
    input_field = None
    
    # Tenta encontrar por ID primeiro
    if element['id']:
        try:
            input_field = page.locator(f"#{element['id']}")
            await input_field.click(timeout=5000)
            await input_field.wait_for(state="editable", timeout=5000)
            return input_field
        except PlaywrightTimeoutError:
            input_field = None
    
    # Se não funcionou por ID, tenta por NAME
    if not input_field and element['name']:
        try:
            input_field = page.locator(f"[name='{element['name']}']")
            await input_field.click(timeout=5000)
            await input_field.wait_for(state="editable", timeout=5000)
            return input_field
        except PlaywrightTimeoutError:
            input_field = None
    
    return input_field

async def submit_form(page, input_field):
    """Submete o formulário usando diferentes estratégias com Playwright"""
    try:
        # Procura por botão submit
        submit_button = page.locator("button[type='submit']")
        await submit_button.click(timeout=3000)
    except PlaywrightTimeoutError:
        try:
            # Procura por botão de login 
            login_button = page.locator("button:has-text('Log in')")
            await login_button.click(timeout=3000)
        except PlaywrightTimeoutError:
            # Pressiona Enter no campo
            await input_field.press("Enter")

async def return_to_original_page(page, original_url):
    """Volta para a página original e fecha modais usando Playwright"""
    try:
        current_url = page.url
        if current_url != original_url:
            await page.goto(original_url, wait_until="domcontentloaded", timeout=10000)
            
            # Aguarda a página carregar e tenta fechar modais novamente
            await page.wait_for_timeout(2000)
            
            # Tenta fechar modal que pode aparecer ao voltar
            try:
                close_button = page.locator("button[class*='close'], button[aria-label*='close'], button:has-text('×')")
                await close_button.first.click(timeout=2000)
            except PlaywrightTimeoutError:
                try:
                    dismiss_button = page.locator("button:has-text('Dismiss'), button:has-text('OK')")
                    await dismiss_button.first.click(timeout=2000)
                except PlaywrightTimeoutError:
                    try:
                        backdrop = page.locator(".cdk-overlay-backdrop")
                        await backdrop.click(timeout=2000)
                    except PlaywrightTimeoutError:
                        try:
                            await page.keyboard.press("Escape")
                        except Exception:
                            pass
    except Exception as e:
        print(f"Erro ao verificar/voltar página: {e}")

async def eco_test(lista, page, test_text):
    """Função de teste para enviar um texto nos campos de input usando Playwright."""
    
    # Salva a URL original para voltar depois de cada teste
    original_url = page.url
    results = []
    
    for element in lista:
        try:
            input_field = None
            # Pula checkboxes e outros tipos não-texto
            if element.get('type') in ['checkbox', 'radio', 'submit', 'button']:
                continue
            
            # Tratamento especial para o campo mat-input-1 (campo de busca)
            if element.get('id') == 'mat-input-1':
                input_field = await activate_mat_input_field(page, 'mat-input-1')
                if not input_field:
                    results.append({
                        'element': element,
                        'status': 'failed',
                        'error': f'Campo de busca mat-input-1 não pode ser ativado'
                    })
                    continue
            else:
                # Tratamento normal para outros campos
                input_field = await find_field_element(page, element)
                    
            if input_field:
                await input_field.clear() 
                await input_field.fill(test_text)

                # Submete o formulário
                await submit_form(page, input_field)
                
                # Aguarda um pouco para a página processar
                await page.wait_for_timeout(2000)
                
                # Verifica se mudou de página após o teste
                current_url = page.url
                eco_result = False
                
                if current_url != original_url:
                    eco_result = await eco_verificator(page, test_text)
                else:
                    # Se não mudou, verifica na página atual
                    eco_result = await eco_verificator(page, test_text)
                
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
        await return_to_original_page(page, original_url)
    
    return results
