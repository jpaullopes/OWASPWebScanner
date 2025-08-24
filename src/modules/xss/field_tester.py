from playwright.async_api import TimeoutError as PlaywrightTimeoutError
import asyncio

async def eco_verificator(page, eco_text):
    """Verifica se o texto enviado foi processado corretamente."""
    try:
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        body_text = page.locator("body").inner_text()
        if eco_text in body_text:
            return True
        return False
    except Exception as e:
        print(f"An error occurred during verification: {e}")
        return False

async def activate_mat_input_field(page, field_id="mat-input-1"):
    """Ativa especificamente o campo mat-input-1 (barra de pesquisa) usando Playwright"""
    try:
        # Verifica se o campo já está ativo
        input_field = page.locator(f"#{field_id}")
        
        # Se já está visível e editável, retorna
        if input_field.is_visible() and input_field.is_editable():
            input_field.focus()
            return input_field
        
        # Se está visível, mas não editável, tenta focar e clicar
        if input_field.is_visible():
            input_field.focus()
            input_field.click()
            page.wait_for_timeout(500)
            
            if input_field.is_editable():
                return input_field
        
        # Tenta encontrar e clicar no ícone de busca para ativar o campo
        search_selectors = [
            "mat-icon.mat-search_icon-search",  
            ".mat-search_icons mat-icon:has-text('search')",  
            "span.mat-search_icons mat-icon[class*='search']", 
        ]
        
        for selector in search_selectors:
            try:
                search_icon = page.locator(selector).first
                if search_icon.count() > 0:
                    search_icon.click(timeout=3000)
                    print(f"Ícone de busca clicado com seletor: {selector}")
                    
                    # Aguarda o campo de input ficar disponível
                    input_field.wait_for(state="visible", timeout=5000)
                    # Tenta focar e clicar no campo
                    input_field.focus()
                    input_field.click()
                    page.wait_for_timeout(500)
                    
                    if input_field.is_editable():
                        return input_field
                    else:
                        page.wait_for_timeout(1000)
                        if input_field.is_editable():
                            return input_field
            except PlaywrightTimeoutError:
                continue
        
        print(f"Não foi possível ativar o campo {field_id}")
        return None
        
    except Exception as e:
        print(f"Erro ao ativar campo {field_id}: {e}")
        return None

async def find_field_element(page, element):
    """Encontra um elemento de campo usando diferentes estratégias com Playwright"""
    input_field = None
    
    # Faz a busca prioritariamente por ID
    if element['id']:
        try:
            input_field = page.locator(f"#{element['id']}")
            input_field.click(timeout=5000)
            input_field.wait_for(state="visible", timeout=5000)
            return input_field
        except PlaywrightTimeoutError:
            input_field = None
    
    # Busca por name se ID não funcionou
    if not input_field and element['name']:
        try:
            input_field = page.locator(f"[name='{element['name']}']")
            input_field.click(timeout=5000)
            input_field.wait_for(state="visible", timeout=5000)
            return input_field
        except PlaywrightTimeoutError:
            input_field = None
    
    return input_field

async def submit_form(page, input_field):
    """Submete o formulário usando diferentes estratégias com Playwright"""
    try:
        # Procura por botão submit específico
        submit_button = page.locator("button[type='submit']").first
        submit_button.click(timeout=3000)
        return
    except PlaywrightTimeoutError:
        pass
    
    try:
        # Procura pelo primeiro botão de login específico 
        login_button = page.locator("button:has-text('Log in')").first
        login_button.click(timeout=3000)
        return
    except PlaywrightTimeoutError:
        pass
    
    try:
        # Procura por botão com ID específico
        login_btn = page.locator("#loginButton")
        if login_btn.count() > 0:
            login_btn.click(timeout=3000)
            return
    except PlaywrightTimeoutError:
        pass
    
    # Pressiona Enter
    try:
        input_field.press("Enter")
    except Exception:
        pass

async def return_to_original_page(page, original_url):
    """Volta para a página original e fecha modais usando Playwright"""
    try:
        current_url = page.url
        if current_url != original_url:
            page.goto(original_url, wait_until="domcontentloaded", timeout=10000)
            
            # Aguarda a página carregar e tenta fechar modais novamente
            page.wait_for_timeout(2000)
            
            # Tenta fechar modal que pode aparecer ao voltar
            try:
                close_button = page.locator("button[class*='close'], button[aria-label*='close'], button:has-text('×')")
                close_button.first.click(timeout=2000)
            except PlaywrightTimeoutError:
                try:
                    dismiss_button = page.locator("button:has-text('Dismiss'), button:has-text('OK')")
                    dismiss_button.first.click(timeout=2000)
                except PlaywrightTimeoutError:
                    try:
                        backdrop = page.locator(".cdk-overlay-backdrop")
                        backdrop.click(timeout=2000)
                    except PlaywrightTimeoutError:
                        try:
                            page.keyboard.press("Escape")
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
                input_field = activate_mat_input_field(page, 'mat-input-1')
                if not input_field:
                    results.append({
                        'element': element,
                        'status': 'failed',
                        'error': f'Campo de busca mat-input-1 não pode ser ativado'
                    })
                    continue
            else:
                # Tratamento normal para outros campos
                input_field = find_field_element(page, element)
                    
            if input_field:
                input_field.clear() 
                input_field.fill(test_text)

                # Submete o formulário
                submit_form(page, input_field)
                page.wait_for_timeout(2000)
                
                # Verifica se mudou de página após o teste
                current_url = page.url
                eco_result = False
                
                if current_url != original_url:
                    eco_result = eco_verificator(page, test_text)
                else:
                    # Se não mudou, verifica na página atual
                    eco_result = eco_verificator(page, test_text)
                
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
        return_to_original_page(page, original_url)
    
    return results
