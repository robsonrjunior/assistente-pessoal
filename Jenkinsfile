pipeline {
  agent any

  options {
    disableConcurrentBuilds()
    timestamps()
  }

  environment {
    DEPLOY_PATH     = '/opt/assistente-pessoal'
    APP_SERVICE_NAME = 'assistente-pessoal'
  }

  triggers {
    pollSCM('H/2 * * * *')
  }

  stages {

    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Validate Branch') {
      steps {
        script {
          def branch = env.BRANCH_NAME ?: env.GIT_BRANCH ?: env.GIT_LOCAL_BRANCH

          if (!branch?.trim()) {
            branch = sh(script: 'git rev-parse --abbrev-ref HEAD', returnStdout: true).trim()
          }

          if (branch == 'HEAD') {
            branch = sh(
              script: "git for-each-ref --format='%(refname:short)' --points-at HEAD refs/remotes/origin | sed -n 's#^origin/##p' | head -n1",
              returnStdout: true
            ).trim()
          }

          branch = branch
            .replaceFirst(/^origin\//, '')
            .replaceFirst(/^refs\/heads\//, '')

          echo "Branch detectada: ${branch}"

          if (branch != 'prod') {
            currentBuild.result = 'NOT_BUILT'
            error("Build ignorado: apenas a branch 'prod' faz deploy. Branch atual: '${branch}'")
          }
        }
      }
    }

    stage('Deploy') {
      steps {
        withCredentials([
          string(credentialsId: 'prod-deploy-host', variable: 'DEPLOY_HOST'),
          string(credentialsId: 'prod-deploy-user', variable: 'DEPLOY_USER'),
          sshUserPrivateKey(credentialsId: 'prod-ssh-key', keyFileVariable: 'SSH_KEY')
        ]) {
          sh '''
            chmod 600 "${SSH_KEY}"

            # Valida que o path de deploy existe no servidor remoto
            ssh -i "${SSH_KEY}" \
              -o IdentitiesOnly=yes \
              -o StrictHostKeyChecking=no \
              ${DEPLOY_USER}@${DEPLOY_HOST} \
              "[ -d ${DEPLOY_PATH} ] || { echo 'ERRO: ${DEPLOY_PATH} não encontrado no servidor.'; exit 1; }"

            # Executa o deploy
            ssh -i "${SSH_KEY}" \
              -o IdentitiesOnly=yes \
              -o StrictHostKeyChecking=no \
              ${DEPLOY_USER}@${DEPLOY_HOST} \
              "cd ${DEPLOY_PATH} && APP_SERVICE_NAME=${APP_SERVICE_NAME} bash scripts/deploy_prod.sh"
          '''
        }
      }
    }
  }

  post {
    success {
      echo "✅ Deploy de '${env.APP_SERVICE_NAME}' finalizado com sucesso. Build #${env.BUILD_NUMBER}"
    }
    failure {
      echo "❌ Falha no pipeline de deploy. Job: ${env.JOB_NAME} | Build: #${env.BUILD_NUMBER}"
      // Descomente e configure conforme sua stack de notificação:
      // slackSend(color: 'danger', message: "❌ Deploy falhou: ${env.JOB_NAME} #${env.BUILD_NUMBER} - ${env.BUILD_URL}")
      // mail(to: 'seu@email.com', subject: "Deploy falhou: ${env.JOB_NAME}", body: "Veja: ${env.BUILD_URL}")
    }
    aborted {
      echo "⚠️ Build abortado ou ignorado (branch diferente de 'prod')."
    }
  }
}
