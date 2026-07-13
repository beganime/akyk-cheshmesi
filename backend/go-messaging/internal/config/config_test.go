package config

import "testing"

func TestIsAllowedOriginAllowsSameHostInProduction(t *testing.T) {
	cfg := Config{AppEnv: "production"}

	if !cfg.IsAllowedOrigin("https://akyl-cheshmesi.ru", "akyl-cheshmesi.ru") {
		t.Fatal("expected a same-host origin to be allowed")
	}
}

func TestIsAllowedOriginRejectsUnknownOriginInProduction(t *testing.T) {
	cfg := Config{AppEnv: "production"}

	if cfg.IsAllowedOrigin("https://example.com", "akyl-cheshmesi.ru") {
		t.Fatal("expected an unknown origin to be rejected")
	}
}

func TestIsAllowedOriginHonorsConfiguredOrigins(t *testing.T) {
	cfg := Config{
		AppEnv:         "production",
		AllowedOrigins: []string{"http://localhost:8081"},
	}

	if !cfg.IsAllowedOrigin("http://localhost:8081", "akyl-cheshmesi.ru") {
		t.Fatal("expected a configured origin to be allowed")
	}
}
