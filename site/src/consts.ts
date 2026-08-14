// Place any global data in this file.
// You can import this data from anywhere in your site by using the `import` keyword.

export const SITE_TITLE = "J'aime les chats";
export const SITE_DESCRIPTION =
	'Le blog de la communauté des amoureux des chats : articles, astuces et tendresse féline, écrits au quotidien.';

export const FACEBOOK_URL = 'https://www.facebook.com/nous.aimons.les.chats';

export const baseUrl = import.meta.env.BASE_URL.replace(/\/+$/, '');
export const url = (path: string) => `${baseUrl}/${path}`.replace(/\/+/g, '/');
