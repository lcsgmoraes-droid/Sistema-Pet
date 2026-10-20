import { FileOutput } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { isAdminRole } from "../../auth/userRole";
import LinkPadrao from "../../components/v2/LinkPadrao/LinkPadrao";

export default function CentralNFSaidaHeader() {
  const { user } = useAuth();
  const podeConfigurar = isAdminRole(user) || user?.permissions?.includes("configuracoes.editar");
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
        <FileOutput className="w-8 h-8 text-purple-600" />
        NF de Saída
      </h1>
      <p className="text-gray-600 mt-1">
        Notas fiscais emitidas pelo CorePet/IntNFe e histórico importado do Bling. Use o painel
        SEFAZ abaixo para consultar ou configurar sincronização.
      </p>
      {podeConfigurar ? (
        <div className="mt-3">
          <LinkPadrao to="/configuracoes/xml-contabilidade">
            XML para contabilidade: baixar, enviar ou agendar
          </LinkPadrao>
        </div>
      ) : null}
    </div>
  );
}
