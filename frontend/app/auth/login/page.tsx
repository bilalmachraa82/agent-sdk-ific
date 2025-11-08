/**
 * Login Page
 * Authentication interface
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { useStore } from '@/lib/store';
import apiClient from '@/lib/api-client';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const { setUser, setTenant } = useStore();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await apiClient.login(email, password);

      // Set user and tenant in store
      setUser({
        id: response.user_id,
        email: response.email,
        name: response.name,
        role: response.role,
        tenant_id: response.tenant_id,
      });

      setTenant({
        id: response.tenant_id,
        slug: response.tenant_slug,
        name: response.tenant_name,
        plan: response.plan,
      });

      // Redirect to dashboard
      router.push('/dashboard');
    } catch (err: any) {
      // Handle different error formats
      let errorMessage = 'Credenciais inválidas. Por favor, tente novamente.';

      if (err.response?.data) {
        const data = err.response.data;

        // Handle Pydantic validation errors (array of objects)
        if (Array.isArray(data.detail)) {
          errorMessage = data.detail.map((e: any) => e.msg || e).join(', ');
        }
        // Handle simple detail string
        else if (typeof data.detail === 'string') {
          errorMessage = data.detail;
        }
        // Handle object detail
        else if (typeof data.detail === 'object' && data.detail !== null) {
          errorMessage = JSON.stringify(data.detail);
        }
      } else if (err.message) {
        errorMessage = err.message;
      }

      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Logo */}
        <div className="text-center">
          <div className="h-12 w-12 bg-primary rounded-lg flex items-center justify-center mx-auto">
            <FileText className="h-7 w-7 text-white" />
          </div>
          <h2 className="mt-6 text-3xl font-bold text-gray-900">
            EVF Portugal 2030
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Automatização de Estudos de Viabilidade Financeira
          </p>
        </div>

        {/* Login Form */}
        <Card>
          <CardHeader>
            <CardTitle>Iniciar Sessão</CardTitle>
            <CardDescription>
              Entre com as suas credenciais para aceder à plataforma
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              )}

              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="seu@email.com"
                  disabled={loading}
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="••••••••"
                  disabled={loading}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <input
                    id="remember"
                    type="checkbox"
                    className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
                  />
                  <label htmlFor="remember" className="ml-2 block text-sm text-gray-900">
                    Lembrar-me
                  </label>
                </div>

                <div className="text-sm">
                  <a href="#" className="font-medium text-primary hover:text-primary/80">
                    Esqueceu a password?
                  </a>
                </div>
              </div>

              <Button
                type="submit"
                className="w-full"
                disabled={loading}
              >
                {loading ? 'A entrar...' : 'Entrar'}
              </Button>
            </form>

            {/* Demo Account Info */}
            <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm font-medium text-blue-900 mb-2">
                Conta Demo
              </p>
              <p className="text-xs text-blue-800">
                Email: demo@evfportugal.pt<br />
                Password: demo123
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-xs text-gray-500">
          &copy; 2025 EVF Portugal 2030. Todos os direitos reservados.
        </p>
      </div>
    </div>
  );
}
