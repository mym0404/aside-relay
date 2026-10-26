import { test, expect, SESSION_A } from './fixture';

test.beforeEach(async ({ page }) => {
  await page.goto(`/c/${SESSION_A}`);
  await expect(page.getByRole('article', { name: 'Response' })).toContainText('Hello from the assistant.');
});

test('typing / opens slash commands and selecting New starts a chat', async ({ page }) => {
  const composer = page.getByRole('textbox', { name: 'Message' });
  await composer.click();
  await composer.pressSequentially('/');

  const menu = page.getByRole('listbox', { name: 'Slash commands' });
  await expect(menu).toBeVisible();
  await expect(menu.getByRole('option', { name: /Clear/ })).toBeVisible();
  await expect(menu.getByRole('option', { name: /New/ })).toBeVisible();

  await composer.pressSequentially('new');
  await expect(menu.getByRole('option', { name: /New/ })).toBeVisible();
  await menu.getByRole('option', { name: /New/ }).click();

  await expect(page).toHaveURL(/\/$/);
  await expect(composer).toHaveValue('');
  await expect(menu).toHaveCount(0);
});

test('selecting a slash skill shows a removable chip, not raw markdown', async ({ page, mockAside }) => {
  mockAside.skills = [
    { name: 'demo-skill', path: 'user/demo-skill', description: 'Demo skill for slash menu', enabled: true },
  ];
  const composer = page.getByRole('textbox', { name: 'Message' });
  await composer.click();
  await composer.pressSequentially('/demo');

  const menu = page.getByRole('listbox', { name: 'Slash commands' });
  await expect(menu.getByRole('option', { name: /demo-skill/ })).toBeVisible();
  await menu.getByRole('option', { name: /demo-skill/ }).click();

  await expect(composer).toHaveValue('');
  await expect(page.getByRole('button', { name: 'Remove demo-skill' })).toBeVisible();
  await expect(page.locator('#composer')).not.toContainText('[@skill');
  await expect(menu).toHaveCount(0);

  await page.getByRole('button', { name: 'Remove demo-skill' }).click();
  await expect(page.getByRole('button', { name: 'Remove demo-skill' })).toHaveCount(0);
});
