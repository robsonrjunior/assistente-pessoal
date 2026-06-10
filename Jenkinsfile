pipeline {
  agent any

  options {
    disableConcurrentBuilds()
    timestamps()
  }

  environment {
    DEPLOY_PATH = '/opt/assistente-pessoal'
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

          branch = branch.replaceFirst(/^origin\//, '').replaceFirst(/^refs\/heads\//, '')
          if (branch != 'prod') {
            currentBuild.result = 'NOT_BUILT'
            error('Build ignorado: apenas a branch prod faz deploy.')
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
            ssh -i "${SSH_KEY}" -o IdentitiesOnly=yes -o StrictHostKeyChecking=no ${DEPLOY_USER}@${DEPLOY_HOST} \
              "cd ${DEPLOY_PATH} && APP_SERVICE_NAME=${APP_SERVICE_NAME} bash scripts/deploy_prod.sh"
          '''
        }
      }
    }
  }

  post {
    success {
      echo 'Deploy finalizado com sucesso.'
    }
    failure {
      echo 'Falha no pipeline de deploy.'
    }
  }
}
