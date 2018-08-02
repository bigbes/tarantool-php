#include "php_tarantool.h"

#include "tarantool_url_ext.h"

php_url *php_url_ext_pecopy(php_url *old_url, int persistent)
{
	php_url *url = pemalloc(sizeof(php_url), persistent);
	if (old_url->scheme)
		url->scheme   = pestrdup(old_url->scheme, persistent);
	if (old_url->user)
		url->user     = pestrdup(old_url->user, persistent);
	if (old_url->pass)
		url->pass     = pestrdup(old_url->pass, persistent);
	if (old_url->host)
		url->host     = pestrdup(old_url->host, persistent);
	if (old_url->path)
		url->path     = pestrdup(old_url->path, persistent);
	if (old_url->query)
		url->query    = pestrdup(old_url->query, persistent);
	if (old_url->fragment)
		url->fragment = pestrdup(old_url->fragment, persistent);
	return url;
}

php_url *php_url_ext_pemove(php_url *old_url, int persistent)
{
	php_url *url = php_url_ext_pecopy(old_url, persistent);
	php_url_ext_pefree(old_url, 0);
	return url;
}

void php_url_ext_pefree(php_url *theurl, int persistent)
{
	if (theurl->scheme)
		pefree(theurl->scheme, persistent);
	if (theurl->user)
		pefree(theurl->user, persistent);
	if (theurl->pass)
		pefree(theurl->pass, persistent);
	if (theurl->host)
		pefree(theurl->host, persistent);
	if (theurl->path)
		pefree(theurl->path, persistent);
	if (theurl->query)
		pefree(theurl->query, persistent);
	if (theurl->fragment)
		pefree(theurl->fragment, persistent);
	pefree(theurl, persistent);
}
